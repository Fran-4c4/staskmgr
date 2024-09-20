# log_handlers.py
import logging
import psycopg2
from psycopg2 import sql
from datetime import datetime
import time

class PostgreSQLHandler(logging.Handler):
    
    def __init__(self, dsn, table_name='logs', insert_query=None):
        super().__init__()
        self.dsn = dsn
        self.table_name = table_name
        self.insert_query = insert_query or f"""
            INSERT INTO {self.table_name} (timestamp, level, name, message, origin)
            VALUES (%s, %s, %s, %s, %s)
        """
        self.conn = None
        self.cursor = None
        self.setup_connection()

    def setup_connection(self):
        self.conn = psycopg2.connect(self.dsn)
        self.cursor = self.conn.cursor()
        # Opcional: Crear la tabla si no existe
        # self.cursor.execute(sql.SQL(f'''
        #     CREATE TABLE IF NOT EXISTS {self.table_name} (
        #         id SERIAL PRIMARY KEY,
        #         timestamp TIMESTAMP,
        #         level VARCHAR(10),
        #         name VARCHAR(100),
        #         message TEXT,
        #         origin TEXT
        #     )
        # '''))
        self.conn.commit()

    def emit(self, record):
        if self.conn is None or self.cursor is None:
            self.setup_connection()
        # log_entry = self.format(record)
        timestamp=time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(record.created))
        # timestamp = datetime.strptime(record.created, '%Y-%m-%d %H:%M:%S,%f').strftime('%Y-%m-%d %H:%M:%S')
        origin=getattr(record, 'origin', "")
        params=(timestamp, record.levelname, record.name, record.getMessage(),origin)
        self.cursor.execute(self.insert_query,params )
        self.conn.commit()

    def close(self):
        if self.conn is not None:
            self.conn.close()
        super().close()
