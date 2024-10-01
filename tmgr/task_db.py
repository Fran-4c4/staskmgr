import logging
from typing import List
from sqlalchemy.sql import text as sqltext
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import and_


from .db_base import DBBase
from .model.task import Task
from .model.task_dep import TaskDep
from .enums.task_status_enum import TaskStatusEnum


class TaskDB(DBBase):
    """class to manage task queries to DDBB

    Args:
        DBBase (DBBase): Base class for DB handlers
    """    

    def __init__(self,scoped_session=None):
        """init

        Args:
            scoped_session (Session, optional): Session shared. Defaults to None.
        """        
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
            TaskDep: TaskDep
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
        # task = session.query(Task).filter(
        #     and_(
        #         Task.id == str(id),
        #         Task.status == 'active',  
        #         Task.priority > 3        # Another example filter condition
        #     )
        # ).first()
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

    def get_pending_task(self,status_list:list=None, task_types:list=None, limit=1,filter_task_key=None):
        """return pending task

        Args:
            status_list (list, optional): list of types to get. Defaults to None and then it will look for TaskStatusEnum.PENDING.
            task_types (list, optional): list of tasks types to search. Defaults to None.
            limit (int, optional): limit of task to retrieve. Defaults to 1.
            filter_task_key (str, optional): task manager key used to filter when the same table is used by diferent managers. Defaults to None.

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
            
            if filter_task_key is not None:
                sql+= """ and id_tmgr ilike  :id_tmgr """    
                params["id_tmgr"]=filter_task_key             
                              
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
        

    def reset_status(self,filter_task_key=None):
        """reset status for tasks when the taskmanager restart

        Args:
            filter_task_key (str, optional): task manager key used to filter when the same table is used by diferent managers. Defaults to None.
        Raises:
            Exception: _description_
        """        
        session = self.getsession()
        try:
            sql = """UPDATE tmgr_tasks
                    SET status = :p_new_status
                    , output= :p_output
                    where status ILIKE :p_check_status                                       
            """
            
            params = { 'p_check_status':str(TaskStatusEnum.CHECKING)
                          ,'p_new_status': str(TaskStatusEnum.PENDING)
                           ,'p_output': 'Reset to pending by system reload.'
                          }    
            if filter_task_key is not None:
                sql+= """ and id_tmgr ilike  :id_tmgr """    
                params["id_tmgr"]=filter_task_key
                
            sqltext_query = sqltext(sql)
            result = session.execute(sqltext_query, params)
            session.commit()
            self.log.info("Reset all tasks in Checking status to pending.")
        except SQLAlchemyError as e:
            if hasattr(e, '_message'):
                error_message = e._message  # Usar el mensaje completo si está disponible
            else:
                error_message = " ".join(e.args) if e.args else str(e)
            raise Exception(error_message)

        except Exception as e:
            raise

    def update_status(self, id: str, new_status: TaskStatusEnum, prev_status=None, output=None, **kwargs):
        """update task status

        Args:
            id (str): task id
            new_status (TaskStatusEnum): new status to set.
            prev_status (_type_, optional): filter by this status to update. Defaults to None.
            output (_type_, optional): Any message to set during update. Defaults to None.

        Raises:
            Exception: _description_

        Returns:
            _type_: _description_
        """        
        session = self.getsession()
        try:
            id = str(id)
            sql = """UPDATE tmgr_tasks
                    SET status = :new_status
                    , modify_date= NOW()
            """
            parameters = {'new_status': str(new_status) }

            if output is not None:
                sql += ", output = :output"
                parameters['output'] = str(output)

            sql=self._add_sql_param(key="progress",sql=sql,parameters=parameters,**kwargs)    
            sql=self._add_sql_param(key="time_start",sql=sql,parameters=parameters,**kwargs)
            sql=self._add_sql_param(key="time_end",sql=sql,parameters=parameters,**kwargs)                  

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
        
    def _add_sql_param(self,key:str,sql:str,parameters:dict,**kwargs):
        """helper method to add parameters to query

        Args:
            key (str): key
            sql (str): sql to modify
            parameters (dict): dict parameters to add parametes if needed
        Keyword Arguments:
            - **additional_params**: dict of additional parameters to be added to the SQL query. Defaults to {}
        Returns:
            str: sql modified
        """        
        value = kwargs.get(key, None)
        if value is not None:
            sql += f" , {key} = :{key} "
            parameters[key] = value 
        return sql

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

    def modify(self, task_like_obj)->Task:
        """modify task data.

        Args:
            task_like_obj (dict|Task): Data for modification. In order to modify only some fields normally is expecting dict object. If you pass a Task object all the fields must be filled.

        Raises:
            oex: exception

        Returns:
            Task: Task object modified
        """        
        session =None
        try:
            if isinstance(task_like_obj, dict):
                pass
            elif isinstance(task_like_obj, object):  # Nota: Todos los objetos en Python son instancias de 'object', por lo que esto siempre será True para instancias de clases
                task_dict=self._task_obj_to_dict(task_like_obj)
                
            session =self.getsession()    
            _task = session.query(Task).filter(Task.id == task_dict['id']).one() #raise error if the task doesn´t exists
            if 'type' in task_dict:
                _task.type = task_dict['type']
            if 'parameters' in task_dict:
                _task.parameters = task_dict['parameters']
            if 'id_user' in task_dict:
                _task.id_user = task_dict['id_user']
            if 'status' in task_dict and _task.status!=task_dict['status']:
                _task.status = task_dict['status']
            if 'output' in task_dict:
                _task.output = task_dict['output']
            if 'time_end' in task_dict:
                _task.time_end = task_dict['time_end']
            if 'time_start' in task_dict:
                _task.time_start = task_dict['time_start']
            if 'progress' in task_dict:
                _task.progress = task_dict['progress']
            if 'priority' in task_dict:
                _task.output = task_dict['priority']
            if 'modify_date' in task_dict:
                _task.time_end = task_dict['modify_date']
            if 'scheduled_date' in task_dict:
                _task.time_start = task_dict['scheduled_date']
            if 'recurrence_interval' in task_dict:
                _task.progress = task_dict['recurrence_interval']   
            if 'id_tmgr' in task_dict:
                _task.time_start = task_dict['id_tmgr']
            if 'created_at' in task_dict:
                _task.progress = task_dict['created_at']                                
                
            return _task
        except Exception as oex:
            raise oex

    def get_value(self,container, key, default=None):
        # Si es un diccionario, intenta obtener el valor con get()
        if isinstance(container, dict):
            return container.get(key, default)
        
        # Si es un objeto, intenta acceder al atributo
        elif hasattr(container, key):
            return getattr(container, key, default)
        
        # Si no es ni diccionario ni objeto, retorna el valor por defecto
        return default
    
    def _task_obj_to_dict(self,task_like_obj)-> dict:
        """Convert obj in dictionary

        Args:
            task_like_obj (Task|dict): Data for conversion.

        Returns:
            dict: Task dictionary
        """        
        obj=None
        if isinstance(task_like_obj, dict):
                return task_like_obj
        elif isinstance(task_like_obj, object):  # Nota: Todos los objetos en Python son instancias de 'object', por lo que esto siempre será True para instancias de clases
            obj={}
            obj['type']         =task_like_obj.type
            obj['parameters']   =task_like_obj.parameters
            
            obj['status']       = task_like_obj.status
            obj['output']       =task_like_obj.output  
            obj['time_end']     =task_like_obj.time_end 
            obj['time_start']   =task_like_obj.time_start
            obj['progress']     =task_like_obj.progress
            obj['priority']     =task_like_obj.priority
            obj['modify_date']     =task_like_obj.modify_date
            obj['scheduled_date']  =task_like_obj.scheduled_date
            obj['recurrence_interval']  =task_like_obj.recurrence_interval
            
            # others
            obj['id_tmgr']     =task_like_obj.id_tmgr
            obj['id_user']      =task_like_obj.id_user
            obj['created_at']     =task_like_obj.id_tmgr
            return obj
            



