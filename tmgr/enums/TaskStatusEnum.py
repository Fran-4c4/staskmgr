from .EnumBase import EnumBase

class TaskStatusEnum(str,EnumBase):
    """Enumeration for task
    We use lower case because all the old code is lower case
    """    
    NONE = 'NONE',
    RUNNING = 'RUNNING',
    PENDING = 'PENDING',
    ERROR = 'ERROR',
    FINISHED = 'FINISHED',
    CHECKING = 'CHECKING',
    WAIT_EXECUTION = 'WAIT_EXECUTION',

