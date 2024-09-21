"""
Default execution entry point if running the package via python -m.
"""
import os
import json
import sys
import argparse
import logging
import signal
import textwrap
import traceback
from typing import Dict
from tmgr.log_handlers.postgres_handler import  PostgreSQLHandler
from tmgr.log_handlers.origin_filter import OriginFilter
from tmgr import version

cfg:Dict=None

def init_logging(task_mgr_name='staskmgr',log_path='app.log',use_db_handler=False):
    # Remove logging.basicConfig because it may override your manual settings
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG) 

    # Define formatter with custom 'origin' field
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s - origin: %(origin)s')

    # Apply the custom filter with 'origin' field
    origin_filter = OriginFilter(origin=task_mgr_name)


    # Create handlers
    file_handler = logging.FileHandler(log_path)
    console_handler = logging.StreamHandler()

    # Optionally add the PostgreSQL handler
    if use_db_handler:
        try:
            # Configurar el DSN para PostgreSQL
            dbcfg = json.loads(cfg.get('DDBB_CONFIG'))
            user = dbcfg.get('user')
            password = dbcfg.get('password')
            host = str(dbcfg.get('host'))
            port = str(dbcfg.get('port'))
            db_name = str(dbcfg.get('db'))

            dsn = f"dbname={db_name} user={user} password={password} host={host} port={port}"

            pg_handler = PostgreSQLHandler(
                dsn,
                table_name='tmgr_logs',
            )    
            # pg_handler.setLevel(logging.DEBUG)
            # pg_handler.setFormatter(formatter)
            logger.addHandler(pg_handler)

        except Exception as ex:
            print(f'WARNING: DDBB log handler error {str(ex)}')

    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    for handler in logger.root.handlers:
        # This is lazy and does only the minimum alteration necessary. It'd be better to use
        # dictConfig / fileConfig to specify the full desired configuration from the start:
        # http://docs.python.org/2/library/logging.config.html#dictionary-schema-details
        # handler.setFormatter(CustomFormatter(handler.formatter._fmt))
        handler.setLevel(logging.DEBUG)
        handler.addFilter(origin_filter)
        handler.setFormatter(formatter)



def main(args=None):
    """Run script entry point.
    """
    if args is None:
        args = sys.argv[1:]

    parsed_args = get_args(args)

    try:
        
        task_mgr_name=parsed_args.task_mgr_name
        config_file=parsed_args.config_file
        
        if not os.path.isabs(config_file):
            # If it's not absolute, resolve it relative to the application path
            app_path =sys.path[0] #os.path.dirname(os.path.abspath(__file__))  # Application's base directory
            cfg_path = os.path.abspath(os.path.join(app_path, cfg_path))  # Resolve the relative path
            print(f"config_file path {cfg_path}")
        
        with open(cfg_path, 'r', encoding='utf-8') as mfile:
            cfg= json.load(mfile)
        
        log_path=cfg.get("logging",{}).get("LOGFILE","app_log.log") 
        
        init_logging(task_mgr_name=task_mgr_name,log_path=log_path)
         

        logger = logging.getLogger(__name__)
        logger.info('Starting run.py demo.')
        pl=tmgr.TMgr(config_like=config_file)
        
        pl.monitor_and_execute()

        sys.stderr.write("TASK MANAGER ENDS" )   


    except KeyboardInterrupt:
        # Shell standard is 128 + signum = 130 (SIGINT = 2)
        sys.stdout.write("\n")
        return 128 + signal.SIGINT
    except Exception as e:
        # stderr and exit code 255
        sys.stderr.write("\n")
        sys.stderr.write(f"\033[91m{type(e).__name__}: {str(e)}\033[0;0m")
        sys.stderr.write("\n")
        # at this point, you're guaranteed to have args and thus log_level
        if parsed_args.log_level:
            if parsed_args.log_level < 10:
                # traceback prints to stderr by default
                traceback.print_exc()

        return 255

# region cli args


def get_args(args):
    """Parse arguments passed in from shell."""
    return get_parser().parse_args(args)


def get_parser():
    """Return ArgumentParser"""
    parser = argparse.ArgumentParser(
        allow_abbrev=True,
        description='stmgr execution',
        formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('task_mgr_name',
                        help=wrap('Name of task manager to run.'))
    
    parser.add_argument(dest='config_file',
                        nargs='*',
                        default=None,
                        help=wrap('Pass config file. Use absolute path or relative path'))
    
    parser.add_argument('--version', action='version',
                        help='Echo version number.',
                        version=f'{version.get_version()}')
    return parser


def wrap(text, **kwargs):
    """Wrap lines in argparse
    
    """
    text = text.splitlines()
    text = [textwrap.fill(line, **kwargs) for line in text]
    return '\n'.join(text)

if __name__ == '__main__':
    sys.exit(main())
