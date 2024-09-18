import os
import logging


class LogHelper():
    """
    Class helper to configure log
    """    

    @staticmethod
    def initLogging(file_path:str,configuration:dict):
        """
        Initialize logger

        Args:
            rootPath (str): path for log file
            configSection (dict): Configuration with the logging options.
        """      

        DEFAULT_LOG_FORMATTER = configuration.get('DEFAULT_LOG_FORMATTER')  
        if DEFAULT_LOG_FORMATTER is None:
            DEFAULT_LOG_FORMATTER = "%(asctime)s %(levelname)s %(name)s.%(funcName)s.%(lineno)d - %(message)s"
        
        DEFAULT_LOG_LEVEL = configuration.get('DEFAULT_LOG_LEVEL')
        if DEFAULT_LOG_LEVEL is None:
            DEFAULT_LOG_LEVEL = logging.DEBUG

        DATE_FORMAT=configuration.get('DEFAULT_LOG_DATE_FORMAT')
        if DATE_FORMAT is None:
            DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
        
        LOGFILE=configuration.get("LOGFILE")
        if LOGFILE is None:
            print('Logfile is none')
            return
        
        backupCount=configuration.get("backupCount",10)
        maxBytes=configuration.get("maxBytes",1024 * 1024 * 512)

        logging.basicConfig(format=DEFAULT_LOG_FORMATTER, level=DEFAULT_LOG_LEVEL)
        fileLogging = os.path.join(file_path, LOGFILE)
        print('Writing log to file...%s' % fileLogging)
        rotatingHandler = logging.handlers.RotatingFileHandler(fileLogging, maxBytes=maxBytes, backupCount=backupCount)
        
        formatter = logging.Formatter(DEFAULT_LOG_FORMATTER, datefmt=DATE_FORMAT)
        rotatingHandler.setFormatter(formatter)
        
        logging.getLogger('').addHandler(rotatingHandler)            
        logging.getLogger(__name__).info('App Logging  initialized...')
        
class DatabaseHandler(logging.Handler):
    log_table="log"
    
    def __init__(self, connection, log_table="log"):
        self.log_table=log_table
        logging.Handler.__init__(self)
        self.connection = connection
    
    def emit(self, record,type_entry="service"):
        
        cursor = self.connection.cursor()
        log_entry = self.format(record)
        cursor.execute(f"INSERT INTO {self.log_table} (type,message, level) VALUES (?, ?, ?)", (type_entry,log_entry, record.levelname))
        self.connection.commit()
