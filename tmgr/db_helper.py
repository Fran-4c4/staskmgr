import psycopg
import sqlite3
import logging
import os

class DBHelper:
    """
    Simple Generic class to manage connection to DDBB
    """
    def __init__(self, db_type="POSTGRES", **kwargs):
        self.log = logging.getLogger(__name__) 
        
        self.db_type = str(db_type).upper()
        self.log.info(f"DDBB type is {self.db_type}")
        self.connection = None
        
        self.host=kwargs.get("host")
        self.database=kwargs.get("database")
        self.user=kwargs.get("user")
        self.password=kwargs.get("password")
        self.port=kwargs.get("port")       

        if self.db_type == "POSTGRES":
            self.connection = self.config_postgresql()
        elif self.db_type == "SQLITE":
            self.connection =self.config_sqllite()
            
    def close_connection(self):
        if self.connection:
            self.connection.close()
            
    def open_connection(self):
        if self.connection:
            self.connection.close()            
    

    def execute_query(self, query, params=None):
        cursor = self.connection.cursor()
        try:
            cursor.execute(query, params)
            self.connection.commit()
            if query.strip().upper().startswith("SELECT"):
                return cursor.fetchall() 
            else:
                pass 
        except Exception as e:
            print(f"Error ejecutando la consulta: {e}")
            self.connection.rollback()  
        finally:
            cursor.close()


    def config_postgresql(self):
        self.connection = psycopg.connect(
                host=self.host,
                database=self.database,
                user=self.user,
                password=self.password,
                port=self.port
            )
        return self.connection
        
    def config_sqllite(self):
        self.connection = sqlite3.connect(self.database)
        return self.connection

if __name__ == '__main__':      
    # Ejemplo de uso para PostgreSQL:
    db_config = {
        "host": "localhost",
        "database": "mi_base_de_datos",
        "user": "mi_usuario",
        "password": "mi_contraseña",
        "port": "5432"
    }
    configuration_file=F"appconfig.json"
    # Conexión a una base de datos PostgreSQL
    
    db = DBHelper(db_type="postgres", **db_config)

    # Ejecutar una consulta
    test_rows = db.execute_query("SELECT * FROM tmgr_tasks limit 10")
    print(test_rows)
    db.close_connection()    
