import logging

class LogCustomFormatter(logging.Formatter):
    """creates a custom formmater

    Args:
        logging (logging.Formatter): logging.Formatter
    """    
    def _getLoggerName(self, record):
        name = str(record.name)
        if 'DBBase' in name:
            name = name.replace('DBBase', '')
        return name

    def formatException(self, exc_info):
        # Llama al método de la clase base (logging.Formatter) 
        # para obtener el stack trace completo.
        return super().formatException(exc_info)
    
    def format(self, record):       
        # Usa el formato definido en el constructor de la clase base,
        log_line = super().format(record)
        return log_line

