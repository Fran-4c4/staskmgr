
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
import urllib.parse
from sqlalchemy.ext.declarative import declarative_base

from .db_base import DBBase

Base = declarative_base()

class DBMgr():
    """Generic DDBB mgr
    """    
    

    def init_database(self,cfg:dict):
        """
        Creates the connection with the database.

        Args:
            cfg (dict): Configuration data with the information of the connection to the db.

        Raises:
            oEx: SQLAlchemyError.
        """
        log = logging.getLogger(__name__)
        
        db_type=cfg.get('db_type',"POSTGRES")
        
        user=urllib.parse.quote( cfg.get('user'))    
        password=urllib.parse.quote(cfg.get('password'))
        host=str(cfg['host'])
        port=cfg['port']
        db_name=str(cfg['db'])
        
        pool_size= cfg.get('pool_size',200)
        max_overflow= cfg.get('max_overflow',5)
        
        scon=None
        
        if db_type=="POSTGRES":    
            scon =f'postgresql+psycopg://{str(user)}:{str(password)}@{host}:{str(port)}/{str(db_name)}'            
        else:
            raise ValueError("db_type must be POSTGRES")
        
        try:
            DBBase.gDbEngine = create_engine(scon, pool_size=pool_size, max_overflow=max_overflow)
        except SQLAlchemyError as oEx:
            log.exception(oEx)
            raise oEx
            
        if DBBase.gDbEngine is None:
            msg_ex='Couldn\'t initialize connection to DB'
            log.error(msg_ex)        
            DBBase.gDbEngine = None
            raise Exception(msg_ex)
        else:
            Base.metadata.bind = DBBase.gDbEngine
            dbsession = sessionmaker(bind=DBBase.gDbEngine, autoflush=True)
            DBBase.gDBSession = dbsession
