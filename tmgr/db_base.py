import logging
from sqlalchemy.orm import Session,sessionmaker
from sqlalchemy.engine import Engine


class DBBase(object):
    """Base class for database access

    Args:
        object (object): object

    Returns:
        DBBase: DBBase
    """
    # global session shared between instances
    gDbEngine:Engine = None
    gDBSession:sessionmaker = None
    session:Session = None
    scoped_session:Session = None
    log=None

    def __init__(self, scoped_session: Session = None):
        """init

        Args:
            scoped_session (Session, optional): scoped session is the main session used by methods and classes. You must use the same session for all operations included in a trasaction Defaults to None.
        """
        self.log: logging.Logger = logging.getLogger(__name__)
        if scoped_session:
            self.scoped_session = scoped_session

    # Calling destructor
    def __del__(self):
        """
        Closes the existing session.
        """
        # print(__name__ + "DBBase Destructor called")
        try:
            self.closeSession()
        except Exception as ex:
            print(f"DBBase __del__ {str(ex)}" )

    def closeSession(self):
        """
        Closes the existing session if it is exist.
        Do not close the scoped session
        """
        if self.session:
            self.session.close()
            return

    def commit(self):
        """
        If a scoped_session exist makes a commit and return the result. If is not exist, commit the existing session.

        Returns:
            _type_: Commit return.
        """
        if self.scoped_session:
            return self.scoped_session.commit()
        elif self.session:
            return self.session.commit()

    def rollback(self):
        """
        If a scoped_session exist makes a rollback and return the result. If is not exist, rollback the existing session.

        Returns:
            _type_: Rollback return.
        """
        if self.scoped_session:
            return self.scoped_session.rollback()
        elif self.session:
            return self.session.rollback()

    def get_session(self) -> Session:
        return self.getsession()

    def getsession(self) -> Session:
        """
        Returns the existing scoped_session, if is not exist, return the existing session and if is not exist create a new session and return it.

        Returns:
            Session: DB session.
        """
        if self.scoped_session:
            return self.scoped_session
        elif self.session:
            return self.session
        else:
            self.session = DBBase.gDBSession()
            return self.session

    
    def to_dict(self,obj):
        """return an object as dict. Be carefully with this method, only works in some versions of row and sqlalchemy

        Args:
            obj (row): sqlalchemy row

        Returns:
            dict: row to dict
        """        
        # return {column.name: getattr(obj, column.name) for column in obj.__table__.columns}
        return obj._mapping
