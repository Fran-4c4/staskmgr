# db_handlers.py
import logging
import logging.handlers

class RotatingFileHandler(logging.handlers.RotatingFileHandler):
    
    def __init__(self, filename, maxBytes=1024 * 1024 * 512, backupCount=10):
        super().__init__(filename=filename, maxBytes=maxBytes, backupCount=backupCount)
