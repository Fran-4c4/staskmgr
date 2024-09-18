


from enum import Enum


class EnumBase(Enum):
    def __str__(self):
        return f'{self.value}'

