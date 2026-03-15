import logging
from typing import List

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql import text as sqltext

from .async_db_base import AsyncDBBase
from .enums.task_status_enum import TaskStatusEnum


LEASE_COLUMNS = {
    "claimed_by",
    "claim_token",
    "heartbeat_at",
    "lease_until",
    "attempt",
    "external_ref",
    "last_error",
}


class AsyncTaskDB(AsyncDBBase):
    """Async repository used internally by the service runtime."""

    def __init__(self, scoped_session=None):
        super().__init__(scoped_session)
        self.log = logging.getLogger(__name__)

    async def get_task_mgr_configuration(self, task_mgr_id):
        session = self.get_session()
        sql = """SELECT * FROM tmgr_config
                WHERE id ILIKE :task_mgr_id;
                """
        parameters = {"task_mgr_id": task_mgr_id}
        result = await session.execute(sqltext(sql), params=parameters)
        return result.mappings().first()

    async def get_task_definition(self, task_type):
        session = self.get_session()
        sql = """SELECT * FROM tmgr_task_definitions
                WHERE id ILIKE :task_type
                """
        params = {"task_type": task_type}
        result = await session.execute(sqltext(sql), params=params)
        return result.mappings().first()

    async def get_task(self, id_task):
        session = self.get_session()
        sql = "SELECT * FROM tmgr_tasks WHERE id = :id_task"
        result = await session.execute(sqltext(sql), params={"id_task": str(id_task)})
        return result.mappings().first()

    async def get_task_table_columns(self) -> set[str]:
        session = self.get_session()
        sql = """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = current_schema()
              AND table_name = :table_name
        """
        result = await session.execute(sqltext(sql), params={"table_name": "tmgr_tasks"})
        return {row[0] for row in result.fetchall()}

    async def get_schema_capabilities(self) -> dict:
        columns = await self.get_task_table_columns()
        return {
            "task_columns": columns,
            "supports_lease_columns": LEASE_COLUMNS.issubset(columns),
        }

    async def get_pending_task(self, status_list=None, task_types=None, limit=1, filter_task_key=None):
        session = self.get_session()
        try:
            if status_list is None:
                status_list = [str(TaskStatusEnum.PENDING)]
            else:
                status_list = [str(value) for value in status_list]

            sql = """SELECT t.*
                    FROM tmgr_tasks t
                    JOIN tmgr_task_definitions td ON td.id ILIKE t."type"
                    WHERE t.status ILIKE ANY(:status)
            """
            params = {
                "status": status_list,
                "status_dep": str(TaskStatusEnum.FINISHED),
            }

            if filter_task_key is not None:
                sql += """ AND id_tmgr ILIKE :id_tmgr """
                params["id_tmgr"] = filter_task_key

            if task_types is not None:
                task_types = [str(value) for value in task_types]
                sql += """ AND type ILIKE ANY(:task_types) """
                params["task_types"] = task_types

            sql += """ AND (SELECT COUNT(*) FROM tmgr_task_dep td1
                                    JOIN tmgr_tasks t1 ON t1.id = td1.id_task_dep
                                    WHERE td1.id_task = t.id AND t1.status NOT ILIKE :status_dep)=0
                ORDER BY priority DESC, created_at ASC
                """
            if limit > 0:
                sql += """ LIMIT :limit """
                params["limit"] = limit

            result = await session.execute(sqltext(sql), params)
            return result.mappings().first()
        except Exception as oex:
            raise oex

    async def claim_pending_task(
        self,
        task_types=None,
        filter_task_key=None,
        claimed_by=None,
        claim_token=None,
        lease_timeout_seconds=300,
    ):
        session = self.get_session()
        sql = """WITH candidate AS (
                    SELECT t.id
                    FROM tmgr_tasks t
                    JOIN tmgr_task_definitions td ON td.id ILIKE t."type"
                    WHERE t.status ILIKE ANY(:status)
                      AND (SELECT COUNT(*) FROM tmgr_task_dep td1
                           JOIN tmgr_tasks t1 ON t1.id = td1.id_task_dep
                           WHERE td1.id_task = t.id AND t1.status NOT ILIKE :status_dep)=0
                """
        params = {
            "status": [str(TaskStatusEnum.PENDING)],
            "status_dep": str(TaskStatusEnum.FINISHED),
            "new_status": str(TaskStatusEnum.CHECKING),
            "claimed_by": claimed_by,
            "claim_token": claim_token,
            "lease_timeout_seconds": int(lease_timeout_seconds),
            "output": "",
        }

        if filter_task_key is not None:
            sql += """ AND t.id_tmgr ILIKE :id_tmgr """
            params["id_tmgr"] = filter_task_key

        if task_types is not None:
            task_types = [str(value) for value in task_types]
            sql += """ AND t.type ILIKE ANY(:task_types) """
            params["task_types"] = task_types

        sql += """ ORDER BY t.priority DESC, t.created_at ASC
                    LIMIT 1
                    FOR UPDATE SKIP LOCKED
                )
                UPDATE tmgr_tasks t
                SET status = :new_status,
                    output = :output,
                    modify_date = NOW(),
                    claimed_by = :claimed_by,
                    claim_token = :claim_token,
                    heartbeat_at = NOW(),
                    lease_until = NOW() + (:lease_timeout_seconds * interval '1 second'),
                    attempt = COALESCE(attempt, 0) + 1
                FROM candidate
                WHERE t.id = candidate.id
                RETURNING t.*
                """

        result = await session.execute(sqltext(sql), params)
        await session.commit()
        return result.mappings().first()

    async def claim_waiting_task_for_reconciliation(
        self,
        task_types=None,
        filter_task_key=None,
        claimed_by=None,
        claim_token=None,
        lease_timeout_seconds=300,
    ):
        session = self.get_session()
        sql = """WITH candidate AS (
                    SELECT t.id
                    FROM tmgr_tasks t
                    WHERE t.status ILIKE :wait_status
                      AND COALESCE(t.external_ref, '') <> ''
                      AND (t.lease_until IS NULL OR t.lease_until < NOW())
                """
        params = {
            "wait_status": str(TaskStatusEnum.WAIT_EXECUTION),
            "claimed_by": claimed_by,
            "claim_token": claim_token,
            "lease_timeout_seconds": int(lease_timeout_seconds),
        }

        if filter_task_key is not None:
            sql += """ AND t.id_tmgr ILIKE :id_tmgr """
            params["id_tmgr"] = filter_task_key

        if task_types is not None:
            task_types = [str(value) for value in task_types]
            sql += """ AND t.type ILIKE ANY(:task_types) """
            params["task_types"] = task_types

        sql += """ ORDER BY t.modify_date ASC, t.created_at ASC
                    LIMIT 1
                    FOR UPDATE SKIP LOCKED
                )
                UPDATE tmgr_tasks t
                SET claimed_by = :claimed_by,
                    claim_token = :claim_token,
                    heartbeat_at = NOW(),
                    lease_until = NOW() + (:lease_timeout_seconds * interval '1 second'),
                    modify_date = NOW()
                FROM candidate
                WHERE t.id = candidate.id
                RETURNING t.*
                """

        result = await session.execute(sqltext(sql), params)
        await session.commit()
        return result.mappings().first()

    async def reset_status(self, filter_task_key=None, supports_lease_columns=False):
        session = self.get_session()
        try:
            params = {
                "pending_status": str(TaskStatusEnum.PENDING),
                "checking_status": str(TaskStatusEnum.CHECKING),
                "wait_execution_status": str(TaskStatusEnum.WAIT_EXECUTION),
                "output_checking": "Reset to pending by system reload (expired lease).",
                "output_wait_execution": "Reset to pending by system reload before external dispatch was confirmed.",
            }

            if supports_lease_columns:
                sql = """UPDATE tmgr_tasks
                        SET status = :pending_status,
                            output = :output_checking,
                            modify_date = NOW(),
                            claimed_by = NULL,
                            claim_token = NULL,
                            heartbeat_at = NULL,
                            lease_until = NULL
                        WHERE status ILIKE :checking_status
                          AND (lease_until IS NULL OR lease_until < NOW())
                    """
                if filter_task_key is not None:
                    sql += """ AND id_tmgr ILIKE :id_tmgr """
                    params["id_tmgr"] = filter_task_key
                await session.execute(sqltext(sql), params)

                sql = """UPDATE tmgr_tasks
                        SET status = :pending_status,
                            output = :output_wait_execution,
                            modify_date = NOW(),
                            claimed_by = NULL,
                            claim_token = NULL,
                            heartbeat_at = NULL,
                            lease_until = NULL
                        WHERE status ILIKE :wait_execution_status
                          AND COALESCE(external_ref, '') = ''
                          AND lease_until IS NOT NULL
                          AND lease_until < NOW()
                    """
                if filter_task_key is not None:
                    sql += """ AND id_tmgr ILIKE :id_tmgr """
                await session.execute(sqltext(sql), params)
                self.log.info("Reset stale tasks using lease-aware recovery.")
            else:
                sql = """UPDATE tmgr_tasks
                        SET status = :pending_status,
                            output = :output_checking,
                            modify_date = NOW()
                        WHERE status ILIKE :checking_status
                    """
                if filter_task_key is not None:
                    sql += """ AND id_tmgr ILIKE :id_tmgr """
                    params["id_tmgr"] = filter_task_key
                await session.execute(sqltext(sql), params)
                self.log.info("Reset tasks in Checking status to pending.")

            await session.commit()
        except SQLAlchemyError as ex:
            await session.rollback()
            if hasattr(ex, "_message"):
                error_message = ex._message
            else:
                error_message = " ".join(ex.args) if ex.args else str(ex)
            raise Exception(error_message)

    async def touch_lease(self, id_task: str, claim_token: str, lease_timeout_seconds: int):
        session = self.get_session()
        sql = """UPDATE tmgr_tasks
                SET heartbeat_at = NOW(),
                    lease_until = NOW() + (:lease_timeout_seconds * interval '1 second'),
                    modify_date = NOW()
                WHERE id = :id
                  AND claim_token = :claim_token
                  AND status ILIKE :checking_status
            """
        params = {
            "id": str(id_task),
            "claim_token": claim_token,
            "checking_status": str(TaskStatusEnum.CHECKING),
            "lease_timeout_seconds": int(lease_timeout_seconds),
        }
        result = await session.execute(sqltext(sql), params)
        await session.commit()
        return result.rowcount

    async def update_status(
        self,
        id: str,
        new_status: TaskStatusEnum,
        prev_status=None,
        output=None,
        release_claim=False,
        claim_token=None,
        supports_lease_columns=False,
        **kwargs,
    ):
        session = self.get_session()
        try:
            parameters = {
                "id": str(id),
                "new_status": str(new_status),
            }
            set_clauses = [
                "status = :new_status",
                "modify_date = NOW()",
            ]

            if output is not None:
                set_clauses.append("output = :output")
                parameters["output"] = str(output)

            for key, value in kwargs.items():
                if value is None:
                    continue
                if isinstance(value, str) and value.upper() in {"NOW()", "CURRENT_TIMESTAMP"}:
                    set_clauses.append(f"{key} = NOW()")
                else:
                    set_clauses.append(f"{key} = :{key}")
                    parameters[key] = value

            if release_claim and supports_lease_columns:
                set_clauses.extend(
                    [
                        "claimed_by = NULL",
                        "claim_token = NULL",
                        "heartbeat_at = NULL",
                        "lease_until = NULL",
                    ]
                )

            sql = f"UPDATE tmgr_tasks SET {', '.join(set_clauses)} WHERE id = :id"

            if prev_status is not None:
                sql += " AND status ILIKE :prev_status"
                parameters["prev_status"] = str(prev_status)

            if claim_token and supports_lease_columns:
                sql += " AND claim_token = :claim_token"
                parameters["claim_token"] = claim_token

            result = await session.execute(sqltext(sql), parameters)
            await session.commit()
            return {
                "status": str(new_status) if result.rowcount > 0 else "NO_UPDATED",
            }
        except SQLAlchemyError as ex:
            await session.rollback()
            if hasattr(ex, "_message"):
                error_message = ex._message
            else:
                error_message = " ".join(ex.args) if ex.args else str(ex)
            raise Exception(error_message)

    async def get_task_childs(self, id_task, task_types: List = None) -> List:
        session = self.get_session()
        sql = """SELECT COUNT(*) FROM tmgr_task_dep td
                JOIN tmgr_tasks t ON t.id = td.id_task_dep
                WHERE td.id_task = :id_task AND t.status != :status
                """
        params = {"id_task": str(id_task), "status": str(TaskStatusEnum.FINISHED)}

        if task_types:
            sql += " AND t.type ILIKE ANY(:task_types) "
            params["task_types"] = task_types

        sql += " ORDER BY t.priority DESC, t.created_at ASC "
        result = await session.execute(sqltext(sql), params=params)
        return result.fetchall()
