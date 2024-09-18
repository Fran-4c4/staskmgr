"""Simple task manager"""
__name__ = 'simple task manager'
__version__ = '0.0.1'
__author__ = 'Francisco R. Moreno Santana'
__contact__ = 'franrms@gmail.com'
__homepage__ = 'https://staskmgr.github.com'
__docformat__ = 'restructuredtext'
__keywords__ = 'task job queue distributed messaging actor'
__description__ ='Simple task manager to handle execution of tasks in AWS or docker.'

from .TMgr import *
from .task_handler_interface import *
