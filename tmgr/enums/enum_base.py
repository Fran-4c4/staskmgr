


from enum import Enum


class EnumBase(Enum):
    """Base class for enums that return str

    Args:
        Enum (Enum): Enum
    """    
    def __str__(self):
        return f'{self.value}'

