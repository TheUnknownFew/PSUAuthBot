from collections import AsyncGenerator
from functools import wraps
from types import AsyncGeneratorType
from typing import Union

from discord import User

from common.bot.userstatus import ComparableStatus, UserStatus
from common.exceptions import UserMismatchError, UnregisteredUserError, InvalidGlobalOperation
from extensions.user import UserEntry

import aiosqlite as sqlite


_columns: list[str] = ['user_id', 'joined_timestamp', 'first_name', 'last_name',
                       'psu_email', 'status_msg_id', 'dm_channel_id', 'status']
_param_list: str = ''.join(['?, ' for _ in range(len(_columns))]).rstrip(', ')


def user_operation(coro):
    @wraps(coro)
    def wrapper(*args, **kwargs):
        self: UserEntryManager = args[0]
        if not self.is_registered:
            raise UnregisteredUserError(self.contextual_user)
        if self.contextual_user is None:
            raise InvalidGlobalOperation(self, coro.__name__)

        coro_inst = coro(*args, **kwargs)
        if isinstance(coro_inst, AsyncGeneratorType):
            async def inner():
                async for val in coro_inst:
                    yield val
        else:
            async def inner():
                return await coro_inst
        return inner()
    return wrapper


def global_operation(coro):
    @wraps(coro)
    def wrapper(*args, **kwargs):
        coro_inst = coro(*args, **kwargs)
        if isinstance(coro_inst, AsyncGeneratorType):
            async def inner():
                async for val in coro_inst:
                    yield val
        else:
            async def inner():
                return await coro_inst
        return inner()
    return wrapper


class UserEntryManager:
    def __init__(self, user: User = None):
        """
        Database connection manager used for managing user data:\n
        Contexts - Global, User

        **Global:** Specified if no user was passed to `__init__` \n
        A global context can be used when a user is not required to fetch data from the database.
        A global context is less restrictive than a User context.

        **User:** Specified if a discord user was passed to `__init__` \n
        A user context must be used in order to fetch data about a specific user.

        :param user: A discord User or None. Some operations cannot be executed if user is None.
        """
        self.__user: User = user
        self.__is_registered: bool = False
        self.__con: sqlite.Connection

    async def __aenter__(self):
        """

        :return:
        """
        self.__con = await sqlite.connect('../user_entry.db')
        await self.__con.executescript(
            """
            PRAGMA foreign_keys = ON;
            CREATE TABLE IF NOT EXISTS users (
                user_id UNSIGNED BIG INT PRIMARY KEY,
                joined_timestamp FLOAT NOT NULL,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                psu_email TEXT NOT NULL UNIQUE,
                status_msg_id UNSIGNED BIG INT NOT NULL,
                dm_channel_id UNSIGNED BIG INT NOT NULL,
                status TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS images (
                user_ref_id UNSIGNED BIG INT,
                url TEXT NOT NULL UNIQUE,
                FOREIGN KEY(user_ref_id) REFERENCES users(user_id)
            );
            """)
        if self.__user is not None:
            async with self.__con.execute("SELECT EXISTS(SELECT 1 FROM users WHERE user_id=?)", (self.__user.id,)) as cur:
                row_exists, = await cur.fetchone()
                self.__is_registered = bool(row_exists)
        return self

    @property
    def is_registered(self) -> bool:
        return self.__is_registered

    @property
    def contextual_user(self) -> Union[User, None]:
        return self.__user

    @global_operation
    async def get_unverified_users(self) -> AsyncGenerator[UserEntry, None]:
        not_statuses = (UserStatus.VERIFIED.name, UserStatus.DENIED.name)
        async with self.__con.execute("SELECT * FROM users WHERE status!=? OR status!=?", not_statuses) as cur:
            async for vals in cur:
                yield UserEntry(*vals)

    @global_operation
    async def register_user(self, user_entry: UserEntry):
        """
        Adds a UserEntry to the database.

        :param user_entry: The UserEntry to add to the database.
        """
        await self.__con.execute(f"INSERT OR IGNORE INTO users VALUES ({_param_list})", user_entry.as_tuple())
        if self.__user is not None:
            self.__is_registered = True
        await self.update_user_images(user_entry.image_urls)

    @user_operation
    async def get_user_images(self) -> list[str]:
        """
        Gets the images associated with the context User.

        :return: A list of image urls.
        """
        async with self.__con.execute("SELECT url FROM images WHERE user_ref_id=?", (self.__user.id,)) as cur:
            return [url async for url, in cur]

    @user_operation
    async def delete_user_images(self):
        """
        Deletes all images associated with the context User.
        """
        await self.__con.execute("DELETE FROM images WHERE user_ref_id=?", (self.__user.id,))

    @user_operation
    async def update_user_images(self, image_url_list: list[str]):
        """
        Updates the list of images associated with the context User.

        :param image_url_list: A list of urls to insert into the image table.
        """
        await self.delete_user_images()
        for url in image_url_list:
            await self.__con.execute("INSERT OR IGNORE INTO images (user_ref_id, url) VALUES (?, ?)", (self.__user.id, url))

    @user_operation
    async def get_user_entry(self) -> UserEntry:
        """
        Fetches a the context User's UserEntry from the database.

        :return: Returns a UserEntry with the data of the context User.
        """
        async with self.__con.execute("SELECT * FROM users WHERE user_id=?", (self.__user.id,)) as cur:
            vals, urls = await cur.fetchone(), await self.get_user_images()
            return UserEntry(*vals, urls)

    @user_operation
    async def update_user(self, user_entry: UserEntry):
        """
        Updates the context User's data with a new UserEntry.

        :param user_entry: The UserEntry to update the context User's data with.
        :raises UserMismatchError: Raised if the UserEntry passed does not belong to the context User. i.e. the User ids
        are mismatched.
        """
        if self.__user.id != user_entry.user_id:
            raise UserMismatchError(user_entry, self.__user)
        await self.__con.execute(
            """
            UPDATE users
            SET user_id=?,
                joined_timestamp=?,
                first_name=?,
                last_name=?,
                psu_email=?,
                status_msg_id=?,
                dm_channel_id=?,
                status=?
            WHERE user_id=?
            """, (*user_entry.as_tuple(), user_entry.user_id))
        await self.update_user_images(user_entry.image_urls)

    @user_operation
    async def remove_user(self):
        """
        Removes the context User from the database.
        """
        await self.delete_user_images()
        await self.__con.execute("DELETE FROM users WHERE user_id=?", (self.__user.id,))

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.__con.commit()
        await self.__con.close()

    def __repr__(self) -> str:
        context = 'Global' if self.__user is None else 'User'
        return f'UserDataManager(context={context}, user={self.__user}, user_registered={self.__is_registered})'


async def is_user_registered_with_status(user: User, status_check: ComparableStatus) -> bool:
    """

    :param user:
    :param status_check:
    :return:
    """
    async with UserEntryManager(user) as _user:
        if _user.is_registered:
            user_entry = await _user.get_user_entry()
            return status_check(user_entry.status)
    return False
