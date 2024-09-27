import logging

class LogCustomFormatter(logging.Formatter):
    """creates a custom formmater

    Args:
        logging (logging.Formatter): logging.Formatter
    """    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def formatException(self, etype):
        
        return f"EXCEPTION: {str(etype)}"

    def format(self, record):
        # Personalizar el formato de registro
        if record.exc_info:
            message = self.formatException(record)
        else:
            message = record.getMessage()
        return f"{record.asctime} - {record.levelname} - {self._getLoggerName(record)}{record.name}.{record.funcName}:{record.lineno} - {message}"

    def _getLoggerName(self, record):
        # Obtener el nombre del logger sin la clase base
        name = str(record.name)
        if 'DBBase' in name:
            name = name.replace('DBBase', '')
        return name

# Crear un formatter y configurarlo con el nuevo formato personalizado
# formatter = LogCustomFormatter('%(asctime)s - %(levelname)s - %(name)s-%(funcName)s.%(lineno)d - %(message)s')