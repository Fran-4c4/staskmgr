'''
- author: angel.velazquez@geoaitech.com angel.velazquez@geoaitech.com
'''

import logging
from typing import Any, List
from sqlalchemy.sql import text as sqltext
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy import and_


from .db_base import DBBase
from .model.task import Task
from .enums.task_status_enum import TaskStatusEnum
from .model.task_dep import TaskDep

class TaskDB(DBBase):

    def __init__(self,scoped_session=None):
        super().__init__(scoped_session)
        self.log= logging.getLogger(__name__)

    def get_task_mgr_configuration(self,task_mgr_id):
        """return task manager configuration

        Args:
            task_mgr_id (str): task_mgr_id 

        Raises:
            Exception: Exception

        Returns:
            Row: data for task manager
        """        
        session = self.getsession()
        sql="""SELECT * FROM tmgr_config  
                WHERE id ILIKE :task_mgr_id;
                """
        parameters = {'task_mgr_id': task_mgr_id}
        
        query_res= session.execute(sqltext(sql),params=parameters).fetchone() 
        if query_res:
            obj=self.to_dict(query_res)
        return obj


    def add(self, type, parameters):
        """Add a task to DDBB

        Args:
            type (str): task type
            parameters (str|dict): dict or string with parameters for task

        Raises:
            oEx: _description_

        Returns:
            Task: Task
        """        
        session = self.getsession()
        obj = Task(
            type       = type,
            parameters = parameters,
            status     = str(TaskStatusEnum.PENDING)
            )
        session.add(obj)
        return obj

        
    def add_dependency(self, id_task, id_task_dep):
        """add task dependencies

        Args:
            id_task (uuid): id_task. This is the dependent task
            id_task_dep (uuid): id of the required task.

        Raises:
            oEx: Exception

        Returns:
            _type_: TaskDep
        """        
        session = self.getsession()
        obj = TaskDep(
            id_task    = id_task,
            id_task_dep = id_task_dep
            )
        session.add(obj)
        return obj

    def get_task(self,id) -> Task:
        """return task by id

        Args:
            id (uuid|str): id task

        Raises:
            DBException: DBException

        Returns:
            task: task
        """        
        session = self.getsession()
        obj:Task = session.query(Task).filter(Task.id==str(id)).first()
        return obj
    
    def get_task_available(self,id) -> Task:
        """return task by id

        Args:
            id (uuid|str): id task

        Raises:
            DBException: DBException

        Returns:
            task: task
        """        
        session = self.getsession()
        obj:Task = session.query(Task).filter(Task.id==str(id)).first()
        task = session.query(Task).filter(
            and_(
                Task.id == str(id),
                Task.status == 'active',  
                Task.priority > 3        # Another example filter condition
            )
        ).first()
        return obj    

    def get_task_definition(self,task_type):
        """return task definition by id

        Args:
            task_type (str): task_type 

        Raises:
            Exception: Exception

        Returns:
            Row: data for task
        """        
        session = self.getsession()
        sql="""SELECT * FROM tmgr_task_definitions  
                WHERE id ILIKE :task_type 
                """
        params = {'task_type': task_type}     
        query_res= session.execute(sqltext(sql),params=params).fetchone() 
        return query_res

    def get_pending_task(self,status_list:list=None, task_types:list=None, limit=1):
        """return pending task

        Args:
            status_list (list, optional): list of types to get. Defaults to None and then it will look for TaskStatusEnum.PENDING.

        Raises:
            oEx: exception

        Returns:
            task: task row object
        """ 
        session = self.getsession()
        try:
            if status_list is None:
                status_list=[str(TaskStatusEnum.PENDING)]
            else:
                status_list = [str(value) for value in status_list]

            sql="""SELECT t.* 
                    FROM tmgr_tasks t 
                    join tmgr_task_definitions td on td.id ilike t."type" 
                    WHERE t.status ilike  Any (:status) """
                    
            params = {'status': status_list
                          ,"status_dep":str(TaskStatusEnum.FINISHED)
                          }     
                              
            if task_types is not None:
                task_types = [str(value) for value in task_types]
                sql+= """ and type ilike  Any (:task_types) """    
                params["task_types"]=task_types  
                    
            sql+=     """ and (SELECT COUNT(*) FROM tmgr_task_dep td1
                                    JOIN tmgr_tasks t1 ON t1.id = td1.id_task_dep
                                    WHERE td1.id_task = t.id AND t1.status not ILIKE :status_dep)=0
                order by priority desc, created_at  asc 
                
                """   
            if limit>0:     
                sql+= """ LIMIT :limit """        
                params["limit"]=limit      
   
            sqltext_query = sqltext(sql)
            query_res = session.execute(sqltext_query, params).fetchone()       
                    
            # query_res= session.execute(sqltext(sSQL)).fetchone()
            return query_res
        except Exception as oEx:
            raise oEx
        finally:
            # self.closeSession()   
            pass    
    
    def get_task_childs(self,id_task,task_types:List=None) -> List:
        """return tasks that depends on task passed.

        Args:
            id_task (uuid): id_task
            task_types (List, optional): task types to find, useful when this task manager can´t handle all tasks. Defaults to None.

        Returns:
            List: list of task objects
        """        
        session = self.getsession()
        id_task=str(id_task)

        sql="""SELECT COUNT(*) FROM tmgr_task_dep td
                JOIN tmgr_tasks t ON t.id = td.id_task_dep
                WHERE td.id_task = :id_task AND t.status != :status 
                
                """       
        params = {'id_task': str(id_task), "status":str(TaskStatusEnum.FINISHED)} 
        
        if task_types:
            sql+=" and T.type ilike  Any (:task_types) "
            params["task_types"]=task_types
            
        sql+=" order by t.priority desc , t.created_at asc "         
                 
        query_res= session.execute(sqltext(sql),params=params).fetchall() 
        childs = query_res
        return childs 
        
    def get_task_dependencies_count(self,id_task):
        """return number of dependencies active

        Args:
            id_task (uuid|str): id task

        Raises:
            DBException: DBException

        Returns:
            Task: Task
        """        
        session = self.getsession()
        id_task=str(id_task)

        sSQL=f"""SELECT COUNT(*) FROM tmgr_task_dep td
                JOIN tmgr_tasks t ON t.id = td.id_task_dep
                WHERE td.id_task = {str(id_task)} AND t.status != '{str(TaskStatusEnum.FINISHED)}';
                """                
                
        query_res= session.execute(sqltext(sSQL)).fetchone() 
        dependencies = query_res[0]
        return dependencies 
        




    def update_status(self, id: str, new_status: TaskStatusEnum, prev_status=None, output=None, **kwargs):
        session = self.getsession()
        try:
            id = str(id)
            sql = """UPDATE tmgr_tasks
                    SET status = :new_status
            """
            parameters = {'new_status': str(new_status)}

            if output is not None:
                sql += ", output = :output"
                parameters['output'] = str(output)

            progress = kwargs.get("progress", None)
            if progress is not None:
                sql += ", progress = :progress"
                parameters['progress'] = progress

            sql += " WHERE id = :id"
            parameters['id'] = id

            if prev_status is not None:
                sql += " AND status ILIKE :prev_status"
                parameters['prev_status'] = str(prev_status)

            sqltext_query = sqltext(sql)
            result = session.execute(sqltext_query, parameters)
            session.commit()
            response = {
                "status": None
            }
            if result.rowcount > 0:
                response['status'] = str(new_status)
            else:
                response['status'] = "NO_UPDATED"

            return response
        except SQLAlchemyError as e:
            if hasattr(e, '_message'):
                error_message = e._message  # Usar el mensaje completo si está disponible
            else:
                error_message = " ".join(e.args) if e.args else str(e)
            raise Exception(error_message)

        except Exception as e:
            raise


        
    def modify(self, task):
        """not used

        Args:
            task (_type_): _description_

        Raises:
            oEx: _description_

        Returns:
            _type_: _description_
        """        
        session = self.getsession()
        try:
            _task = session.query(Task).filter(Task.id == task['id']).one()
            if 'status' in task and _task.status!=task['status']:
                _task.status = task['status']
            if 'output' in task:
                _task.output = task['output']
            if 'time_end' in task:
                _task.time_end = task['time_end']
            if 'time_start' in task:
                _task.time_start = task['time_start']
            if 'progress' in task:
                _task.progress = task['progress']
            if 'type' in task:
                _task.type = task['type']
            if 'parameters' in task:
                _task.parameters = task['parameters']
            session.commit()
            return _task
        except Exception as oEx:
            raise oEx
        finally:
            # self.closeSession()
            pass
        
    from sqlalchemy import text

    def get_task_flow(self, id_task):
        # Define the raw SQL query with a parameter placeholder
        session = self.getsession()
        query = sqltext("""
        WITH RECURSIVE task_order AS (
            -- Anchor query: Start from the specific task (task that you pass as an input)
            SELECT t.id, t.status, t.type, t.created_at
            FROM tmgr_tasks t
            WHERE t.id = :task_id  -- Pass your specific task ID here
            AND t.status ILIKE ANY (ARRAY['PENDING', 'WAIT_EXECUTION'])
        
            UNION ALL
        
            -- Recursive part: Find tasks that depend on the previous task
            SELECT td.id_task, t.status, t.type, t.created_at
            FROM tmgr_task_dep td
            INNER JOIN task_order to1 ON td.id_task_dep = to1.id
            INNER JOIN tmgr_tasks t ON td.id_task = t.id
            WHERE t.status ILIKE ANY (ARRAY['PENDING', 'WAIT_EXECUTION'])
        )
        -- Final selection of tasks in dependency order
        SELECT *
        FROM task_order
        ORDER BY created_at;
        """)

        # Execute the query with the provided task ID
        result = session.execute(query, {'task_id': id_task})
        
        # Fetch all results and return them
        return result.fetchall()
