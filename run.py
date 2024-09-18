import os
import logging
from tmgr import TMgr

app_config={}

def init_logging():

    logging.basicConfig(filename='app.log', encoding='utf-8', level=logging.DEBUG)

if __name__ == "__main__":

    config_like="appconfig.json" 
    curDir = os.path.dirname(os.path.abspath(__file__))
    full_path = os.path.join(curDir, 'config', config_like)
    config_like=full_path

    try:           
        init_logging()
        logger = logging.getLogger(__name__)
        logger.info('Starting run.py demo.')
        pl=TMgr(config_like=config_like)
        
        pl.monitor_and_execute()

        print("TASK MANAGER ENDS" )   

    except Exception as oEx:
        print('TASK MANAGER Exception [%s]' % str(oEx))
