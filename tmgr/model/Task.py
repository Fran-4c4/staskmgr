#!/usr/bin/python
# -*- coding: utf-8 -*-
from typing import Type
from sqlalchemy.ext.declarative import DeclarativeMeta
from sqlalchemy import func
from sqlalchemy import Column, String, Integer,  TIMESTAMP, Text, JSON, SmallInteger
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship


from .base_manager import BaseManager
BASE_ORM:Type[DeclarativeMeta]=BaseManager.get_base()

class Task(BASE_ORM):
    """ Task model that holds information about the process to be executed.

    Args:
        base_orm (declarative_base): declarative_base
    """    
    __tablename__ = 'tmgr_tasks'
    
    id = Column(UUID(as_uuid=False), primary_key=True, default=func.uuid_generate_v1())
    # id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid1, nullable=False)
    id_tmgr = Column(Text, nullable=False, default='MAIN')
    status = Column(Text, nullable=False)
    type = Column(Text, nullable=False)
    # type = Column(Text, ForeignKey('tmgr_task_definitions.id'), nullable=False)
    progress = Column(Integer, nullable=False,default=0)
    
    output = Column(Text, nullable=True)
    parameters = Column(JSONB, nullable=True)
    time_start = Column(TIMESTAMP, nullable=True)
    time_end = Column(TIMESTAMP, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), default=func.now(), nullable=True)
    priority = Column(SmallInteger, default=0, nullable=True)
    modify_date = Column(TIMESTAMP, default=func.now(),nullable=True)
    scheduled_date = Column(TIMESTAMP, nullable=True)
    recurrence_interval = Column(TIMESTAMP, nullable=True)
    id_user = Column(Text, nullable=True)
    

    # Relations, we don´t force because definitions can exist in config file
    # task_definition = relationship("TmgrTaskDefinitions", back_populates="tasks")

    # Índices
    # __table_args__ = (
    #     # Índices adicionales definidos explícitamente
    #     {'postgresql_using': 'btree', 'index': True, 'name': 'tmgr_tasks_id_tmgr_idx'},
    #     {'postgresql_using': 'btree', 'index': True, 'name': 'tmgr_tasks_time_start_idx'},
    #     {'postgresql_using': 'btree', 'index': True, 'name': 'tmgr_tasks_type_idx'}
    # )
    
