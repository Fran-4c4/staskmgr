
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
import urllib.parse
from sqlalchemy.ext.declarative import declarative_base

from .DBBase import DBBase

Base = declarative_base()

def initDatabase(cfg:dict):
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
    
    pool_size= cfg.get('pool_size',200)
    max_overflow= cfg.get('max_overflow',5)
    
    scon=None
    if db_type=="POSTGRES":    
        sCon ='postgresql://%s:%s@%s:%d/%s' % (user, password, cfg['host'], cfg['port'], cfg['db'])
    else:
        raise ValueError("db_type must be POSTGRES")
    
    try:
        DBBase.gDbEngine = create_engine(sCon, pool_size=pool_size, max_overflow=max_overflow)
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
