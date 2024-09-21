import logging
import os
import time

class OriginFilter(logging.Filter):
    """log filter to set the origin of the record

    Args:
        logging (logging): Filter
    """    
    def __init__(self, origin=None):
        """init

        Args:
            origin (str, optional): origin. Defaults to None.
        """        
        super().__init__()
        self.origin = origin or os.getpid()

    def filter(self, record):
        record.asctime = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(record.created))
        record.origin = self.origin
        return True
