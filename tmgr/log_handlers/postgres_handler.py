# log_handlers.py
import logging
from typing import Dict
import psycopg2
from psycopg2 import sql
from datetime import datetime
import time

class PostgreSQLHandler(logging.Handler):
    

    
    def __init__(self, config:Dict):
        """init

        Args:
            config (Dict): configuration for handler.Fields expected are:
                - "user" (str): user
                - "password" (str): password
                - "host" (str): host
                - "port" (int): port. Normally 5432 for postgress
                - "db_name" (str): database name
                - "insert_query" (str): query used to insert values. If the query is informed the table name is not used.
                - "log_level" (int): log level, if it is not informed by default is DEBUG
                - "DEFAULT_LOG_FORMATTER" (str): formatter for logs.                
        """        
        super().__init__()
        
        self.dsn = None
        self.table_name = "tmgr_logs"
        self.insert_query = f"""
            INSERT INTO {self.table_name} (timestamp, level, name, message, origin)
            VALUES (%s, %s, %s, %s, %s)
        """
        self.config(cfg=config)
        self.conn = None
        self.cursor = None
        self.setup_connection()

    def setup_connection(self):
        self.conn = psycopg2.connect(self.dsn)
        self.cursor = self.conn.cursor()

    def emit(self, record):
        if self.conn is None or self.cursor is None:
            self.setup_connection()
        # log_entry = self.format(record)
        timestamp=time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(record.created))
        # timestamp = datetime.strptime(record.created, '%Y-%m-%d %H:%M:%S,%f').strftime('%Y-%m-%d %H:%M:%S')
        origin=getattr(record, 'origin', "")
        call_path=f"{record.name}.{record.funcName}:{record.lineno}"
        params=(timestamp, record.levelname, call_path, record.getMessage(),origin)
        self.cursor.execute(self.insert_query,params )
        self.conn.commit()

    def close(self):
        if self.conn is not None:
            self.conn.close()
        super().close()

    
    def config(self,cfg:Dict):
        """Config class. DDBB data is mandatory

        Args:
            cfg (Dict): dict with config data.
        """            
        user = cfg.get('user')
        password = cfg.get('password')
        host = str(cfg.get('host'))
        port = str(cfg.get('port'))
        db_name = str(cfg.get('db'))
        
        self.dsn = f"dbname={db_name} user={user} password={password} host={host} port={port}"
        
        iquery=cfg.get('insert_query')
        if iquery:
            self.insert_query = iquery
        else:
            self.table_name = cfg.get('TMGR_LOG_TABLE',self.table_name) 
            self.insert_query = f"""
            INSERT INTO {self.table_name} (timestamp, level, name, message, origin)
            VALUES (%s, %s, %s, %s, %s)
            """
            
        log_level = cfg.get('LOG_LEVEL',logging.DEBUG) 
        if log_level is None:   
            log_level = cfg.get('log_level',logging.DEBUG)
        self.setLevel(log_level)
        formatter=cfg.get('DEFAULT_LOG_FORMATTER')
        if formatter is None:
            formatter=cfg.get('DEFAULT_LOG_FORMATTER'.lower())
        if formatter is None:
            formatter="'%(asctime)s -  %(levelname)s - %(name)s-%(funcName)s.%(lineno)d - %(message)s - origin: %(origin)s'"
        self.setFormatter(formatter)