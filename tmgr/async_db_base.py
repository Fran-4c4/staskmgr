import logging

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker


class AsyncDBBase:
    """Base class for async database access."""

    gAsyncDbEngine: AsyncEngine = None
    gAsyncSession: async_sessionmaker[AsyncSession] = None
    session: AsyncSession = None
    scoped_session: AsyncSession = None

    def __init__(self, scoped_session: AsyncSession = None):
        self.log = logging.getLogger(__name__)
        if scoped_session:
            self.scoped_session = scoped_session

    async def close_session(self):
        """Close the managed async session if it exists."""
        if self.session:
            await self.session.close()
            self.session = None

    async def commit(self):
        """Commit the current async session."""
        session = self.get_session()
        await session.commit()

    async def rollback(self):
        """Rollback the current async session."""
        session = self.get_session()
        await session.rollback()

    def get_session(self) -> AsyncSession:
        """Return a scoped async session or create a new one."""
        if self.scoped_session:
            return self.scoped_session
        if self.session:
            return self.session
        if AsyncDBBase.gAsyncSession is None:
            raise RuntimeError("Async database session is not initialized.")
        self.session = AsyncDBBase.gAsyncSession()
        return self.session
