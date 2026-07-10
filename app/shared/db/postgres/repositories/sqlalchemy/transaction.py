from sqlalchemy.ext.asyncio import AsyncSession

class SQLAlchemyTransaction:
    def __init__(self, session: AsyncSession):
        self._session = session
        self._txn_cm = None

    async def __aenter__(self):
        if self._session.in_transaction():
            self._txn_cm = self._session.begin_nested()
        else:
            self._txn_cm = self._session.begin()

        await self._txn_cm.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            await self._txn_cm.__aexit__(None, None, None)
            
            if not self._session.in_nested_transaction():
                await self._session.commit()
        else:
            await self._txn_cm.__aexit__(exc_type, exc_val, exc_tb)

    async def commit(self):
        await self._session.commit()

    async def rollback(self):
        await self._session.rollback()