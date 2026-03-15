import logging
import warnings

from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker


def _warn_deprecated_alias(old_name: str, new_name: str) -> None:
    warnings.warn(
        f"`DBBase.{old_name}` is deprecated and will be removed in a future version. "
        f"Use `DBBase.{new_name}` instead.",
        DeprecationWarning,
        stacklevel=3,
    )


class _DBBaseMeta(type):
    @property
    def gDbEngine(cls) -> Engine:
        _warn_deprecated_alias("gDbEngine", "g_db_engine")
        return cls.g_db_engine

    @gDbEngine.setter
    def gDbEngine(cls, value: Engine) -> None:
        _warn_deprecated_alias("gDbEngine", "g_db_engine")
        cls.g_db_engine = value

    @property
    def gDBSession(cls) -> sessionmaker:
        _warn_deprecated_alias("gDBSession", "g_db_session")
        return cls.g_db_session

    @gDBSession.setter
    def gDBSession(cls, value: sessionmaker) -> None:
        _warn_deprecated_alias("gDBSession", "g_db_session")
        cls.g_db_session = value


class DBBase(object, metaclass=_DBBaseMeta):
    """Base class for database access

    Args:
        object (object): object

    Returns:
        DBBase: DBBase
    """
    # Global session shared between instances.
    g_db_engine: Engine = None
    g_db_session: sessionmaker = None
    session: Session = None
    scoped_session: Session = None
    log = None

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
            self.close_session()
        except Exception as ex:
            print(f"DBBase __del__ {str(ex)}")

    def close_session(self):
        """
        Closes the existing session if it is exist.
        Do not close the scoped session
        """
        if self.session:
            self.session.close()
            return

    def closeSession(self):
        """Deprecated alias for close_session."""
        _warn_deprecated_alias("closeSession", "close_session")
        return self.close_session()

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
        """
        Returns the existing scoped_session, if is not exist, return the existing session and if is not exist create a new session and return it.

        Returns:
            Session: DB session.
        """
        if self.scoped_session:
            return self.scoped_session
        if self.session:
            return self.session
        self.session = DBBase.g_db_session()
        return self.session

    def getsession(self) -> Session:
        """Deprecated alias for get_session."""
        _warn_deprecated_alias("getsession", "get_session")
        return self.get_session()

    def to_dict(self, obj):
        """return an object as dict. Be carefully with this method, only works in some versions of row and sqlalchemy

        Args:
            obj (row): sqlalchemy row

        Returns:
            dict: row to dict
        """
        # return {column.name: getattr(obj, column.name) for column in obj.__table__.columns}
        return obj._mapping
