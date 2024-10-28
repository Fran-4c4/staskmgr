"""Simple task manager
   tmgr module 
"""
__name__ = 'simple_task_manager'
__version__     = '1.5.30'
__author__      = 'Francisco R. Moreno Santana'
__contact__     = 'franrms@gmail.com'
__homepage__    = 'https://github.com/Fran-4c4/staskmgr'
__docformat__   = 'text/markdown'
__keywords__    = 'task job queue distributed messaging actor'
__description__ ='Simple task manager to handle execution of tasks in AWS or docker.'
__bug_tracker__ = "https://github.com/Fran-4c4/staskmgr/issues"
__source_code__ = "https://github.com/Fran-4c4/staskmgr"

import time
from .tmgr import TMgr

from .env_loader import *
from .model.task import Task
from .model.task_dep import TaskDep
from .task_handler_interface import TaskHandlerInterface
from .task_db import TaskDB
from .tools import *



#
#_startTime is used as the base when calculating the relative time of events
#
_startTime = time.time()
