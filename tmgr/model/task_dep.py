#!/usr/bin/python
# -*- coding: utf-8 -*-
from typing import Type
from sqlalchemy import Column, ForeignKey
from sqlalchemy.ext.declarative import DeclarativeMeta

from .base_manager import BaseManager
BASE_ORM:Type[DeclarativeMeta]=BaseManager.get_base()

class TaskDep(BASE_ORM):
    """ TaskDep ORM model

    Args:
        base_orm (declarative_base): declarative_base
    """  
    __tablename__ = 'tmgr_task_dep'

    id_task = Column(ForeignKey('tmgr_tasks.id', ondelete='CASCADE', onupdate='CASCADE'), primary_key=True, nullable=False, index=True)
    id_task_dep = Column(ForeignKey('tmgr_tasks.id', ondelete='CASCADE', onupdate='CASCADE'), primary_key=True, nullable=False, index=True)

    
