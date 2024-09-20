import psycopg2
import sqlite3

class DBConnector:
    def __init__(self, db_type="postgres", **kwargs):
        self.db_type = db_type
        self.connection = None

        if self.db_type == "postgres":
            self.connection = psycopg2.connect(
                host=kwargs.get("host", "localhost"),
                database=kwargs.get("database", "test_db"),
                user=kwargs.get("user", "postgres"),
                password=kwargs.get("password", "password"),
                port=kwargs.get("port", "5432")
            )
        elif self.db_type == "sqlite":
            self.connection = sqlite3.connect(kwargs.get("database", "test.db"))

    def execute_query(self, query, params=None):
        cursor = self.connection.cursor()
        try:
            cursor.execute(query, params)
            self.connection.commit()
            if query.strip().lower().startswith("select"):
                return cursor.fetchall()  
        except Exception as e:
            print(f"Error ejecutando la consulta: {e}")
            self.connection.rollback()  
        finally:
            cursor.close()

    def close_connection(self):
        if self.connection:
            self.connection.close()



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
    
    db = DBConnector(db_type="postgres", **db_config)

    # Ejecutar una consulta
    resultados = db.execute_query("SELECT * FROM process")
    print(resultados)

    # Cerrar la conexión
    db.close_connection()    
