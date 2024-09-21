from .enum_base import EnumBase

class LitEnum(str,EnumBase):
    """Enumeration for literals
    """    
    NONE = 'NONE',
    
    task_definition_search_type = 'task_definition_search_type',
    CFG_DB="CFG_DB",
    CFG_ONLY="CFG_ONLY",
    DB_CFG="DB_CFG",
    DB_ONLY="DB_ONLY",
    
    TASK_NEXT_STATUS="task_next_status"