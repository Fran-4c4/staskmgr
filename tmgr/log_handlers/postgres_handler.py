# log_handlers.py
import logging
from typing import Dict
import psycopg2
from psycopg2 import pool
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
        # Initialize connection pool
        self.connection_pool = None
        self.setup_connection_pool()

        
    def setup_connection_pool(self):
        """Set up a connection pool."""
        try:
            self.connection_pool = psycopg2.pool.SimpleConnectionPool(
                1, 100,  # Min 1 connection, max 10 connections in the pool
                dsn=self.dsn
            )
            if not self.connection_pool:
                raise Exception("Connection pool could not be created.")
        except Exception as e:
            raise Exception(f"Error setting up connection pool: {e}")
        
    def get_connection(self):
        """Get a connection from the pool. Check if connection is closed wich is not done by psycopg
        
        """
        if not self.connection_pool:
            self.setup_connection_pool()
            
        conn = self.connection_pool.getconn()    
        
        # Check if the connection is closed
        if conn.closed:
            logging.warning("Connection from pool is closed. Replacing with a new connection.")
            # Remove the invalid connection from the pool
            self.connection_pool.putconn(conn, close=True)
            # Create a new connection
            conn = self.connection_pool.getconn()
            
            
        return conn

    def release_connection(self, conn):
        """Release a connection back to the pool."""
        if self.connection_pool and conn:
            self.connection_pool.putconn(conn)

    def emit(self, record):
        conn = None
        cursor = None
        try:
            # Get a connection from the pool
            conn = self.get_connection()
            cursor = conn.cursor()           
            # log_entry = self.format(record)
            timestamp=time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(record.created))
            # timestamp = datetime.strptime(record.created, '%Y-%m-%d %H:%M:%S,%f').strftime('%Y-%m-%d %H:%M:%S')
            origin=getattr(record, 'origin', "")
            call_path=f"{record.name}.{record.funcName}:{record.lineno}"
            params=(timestamp, record.levelname, call_path, record.getMessage(),origin)
            cursor.execute(self.insert_query,params )
            conn.commit()
            
        except Exception as e:
            if conn:
                conn.rollback()
            logging.error(f"Failed to log to database: {e}")
        
        finally:
            # Ensure cursor is closed and connection is released back to the pool
            if cursor:
                cursor.close()
            if conn:
                self.release_connection(conn)

    def close(self):
        """Close all connections in the pool."""
        if self.connection_pool:
            self.connection_pool.closeall()
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