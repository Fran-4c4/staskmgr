# db_handlers.py
import logging

class SQLiteHandler(logging.Handler):
    
    def __init__(self, db_path,table_name="logs"):
        super().__init__()
        self.table_name=table_name
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        

    def setup_connection(self):
        import sqlite3
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        # Crear la tabla si no existe
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                level TEXT,
                name TEXT,
                message TEXT
            )
        ''')
        self.conn.commit()

    def emit(self, record):
        if self.conn is None or self.cursor is None:
            self.setup_connection()
        log_entry = self.format(record)
        self.cursor.execute('''
            INSERT INTO logs (timestamp, level, name, message)
            VALUES (?, ?, ?, ?)
        ''', (record.asctime, record.levelname, record.name, log_entry))
        self.conn.commit()

    def close(self):
        if self.conn is not None:
            self.conn.close()
        super().close()
