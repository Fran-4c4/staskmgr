from typing import Type
from sqlalchemy.ext.declarative import declarative_base

class BaseManager:
    """base declarative manager

    Returns:
        Type: sqlalchemy.ext.declarative.declarative_base
    """    
    _base:Type = None 

    @classmethod
    def get_base(cls)-> Type:
        # If no base is set, create a default one
        if cls._base is None:
            cls._base = declarative_base()
        return cls._base

    @classmethod
    def set_base(cls, value:Type):
        # Allow external setting of the base
        cls._base = value