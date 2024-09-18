
from typing import Any
from sqlalchemy.ext.declarative import declarative_base

class BaseManager:
    _base:Any = None

    @classmethod
    def get_base(cls):
        # If no base is set, create a default one
        if cls._base is None:
            cls._base = declarative_base()
        return cls._base

    @classmethod
    def set_base(cls, value):
        # Allow external setting of the base
        cls._base = value