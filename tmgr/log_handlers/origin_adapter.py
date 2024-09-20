import logging
import os
import time

class OriginAdapter(logging.LoggerAdapter):
    """log adapter to set the origin of the record

    Args:
        logging (logging): Filter
    """    
    def __init__(self,  logger, extra=None, origin=None):
        """init

        Args:
            origin (str, optional): origin. Defaults to None.
        """        
        super().__init__( logger=logger, extra=extra)
        self.origin = origin or os.getpid()

    def filter(self, record):
        record.asctime = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(record.created))
        record.origin = self.origin
        return True
    
    def process(self, msg, kwargs):
        return '[%s] %s' % (self.origin, msg), kwargs
