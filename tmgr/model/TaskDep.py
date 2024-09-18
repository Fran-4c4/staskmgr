#!/usr/bin/python
# -*- coding: utf-8 -*-
from sqlalchemy import Column, ForeignKey

from .BaseManager import BaseManager
base_orm=BaseManager.get_base()

class TaskDep(base_orm):
    """ TaskDep ORM model

    Args:
        base_orm (declarative_base): declarative_base
    """  
    __tablename__ = 'tmgr_task_dep'

    id_task = Column(ForeignKey('tmgr_task.id', ondelete='CASCADE', onupdate='CASCADE'), primary_key=True, nullable=False, index=True)
    id_task_dep = Column(ForeignKey('tmgr_task.id', ondelete='CASCADE', onupdate='CASCADE'), primary_key=True, nullable=False, index=True)

    
