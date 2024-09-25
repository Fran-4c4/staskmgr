from .enum_base import EnumBase

class LitEnum(str,EnumBase):
    """Enumeration for literals
    """    
    NONE = 'NONE',    
    task_definition_search_type = 'task_definition_search_type',   
    TASK_NEXT_STATUS="task_next_status",
    LAUNCHTYPE_INTERNAL="INTERNAL"
    
class CFGOrderEnum(str,EnumBase):
    """config order to load configuration data
    """     
    CFG_DB="CFG_DB",
    CFG_ONLY="CFG_ONLY",
    DB_CFG="DB_CFG",
    DB_ONLY="DB_ONLY"
     
class FilterTaskKeyEnum(str,EnumBase):    
    """Filter task key enum for origin in task queries

    """    
    ANY_KEY="ANY_KEY",
    SELF_KEY="SELF_KEY"