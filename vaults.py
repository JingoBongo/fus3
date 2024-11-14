import asyncio
import os
import pickle
import constants

from sqlalchemy import Column, LargeBinary, BINARY, select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

from log_utils import logger as log

Base = declarative_base()

class DictEntry(Base):
    __tablename__ = 'dict'
    key = Column(BINARY, primary_key=True, nullable=False)
    value = Column(LargeBinary)

# The MetadataConstructor class is not needed. SQLAlchemy's Base class handles table metadata.

class Vault:
    __slots__ = {"vault_name", "db_path", "__engine__", "__session__", "__metadata__"}

    # in the end i changed to create to true. to be discussed maybe?...
    def __init__(self, vault_name: str, to_create: bool = True):

        self.vault_name = vault_name
        self.db_path = os.path.join(constants.root_path, constants.vaults_folder, f"{vault_name}.db")
        path_exists = os.path.exists(self.db_path)

        if path_exists or to_create:
            db_url = f"sqlite+aiosqlite:///{self.db_path}"
            self.__engine__ = create_async_engine(db_url)
            self.__session__ = sessionmaker(self.__engine__, class_=AsyncSession, expire_on_commit=False)

        if to_create and not path_exists:
            log.info(f"Creating vault '{vault_name}'!")
            asyncio.run(self.__create_table__())

        if not path_exists and not to_create:
            log.error(f"No such vault: '{vault_name}'!")


    async def __create_table__(self):
        async with self.__engine__.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def __put_by_key__(self, key, value):
        async with self.__session__() as session:
            async with session.begin():
                existing_data = await session.get(DictEntry, pickle.dumps(key))
                if existing_data:
                    existing_data.value = pickle.dumps(value)
                else:
                    new_data = DictEntry(key=pickle.dumps(key), value=pickle.dumps(value))
                    session.add(new_data)

    def put(self, key, value):
        asyncio.run(self.__put_by_key__(key, value))

    async def __get_by_key__(self, key):
        async with self.__session__() as session:
            result = await session.execute(select(DictEntry).where(DictEntry.key == pickle.dumps(key)))
            data = result.scalar_one_or_none()
            return pickle.loads(data.value) if data else None

    def get(self, key):
        return asyncio.run(self.__get_by_key__(key))