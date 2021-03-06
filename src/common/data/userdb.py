from functools import wraps
from types import AsyncGeneratorType
from typing import Optional, AsyncGenerator

from discord import User

import aiosqlite as sqlite

from common.bot.userstatus import UserStatus
from common.data.userdetails import UserDetails
from common.exceptions import UserMismatchError, UnregisteredUserError, InvalidGlobalOperation


_columns: list[str] = ['user_id', 'joined_timestamp', 'first_name', 'last_name', 'psu_email', 'status_msg_id', 'dm_channel_id', 'status']
_param_list: str = ''.join(['?, ' for _ in range(len(_columns))]).rstrip(', ')


def user_operation(coro):
    @wraps(coro)
    def wrapper(*args, **kwargs):
        self: UserEntryManager = args[0]
        if not self.is_registered:
            raise UnregisteredUserError(self.discord_user)
        if self.discord_user is None:
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
        self.__user: Optional[User] = user
        self.__is_registered: bool = False
        self.__conn: sqlite.Connection

    async def __aenter__(self):
        """

        :return:
        """
        self.__conn = await sqlite.connect('../user_entry.db')
        await self.__conn.executescript(
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
            async with self.__conn.execute("SELECT EXISTS(SELECT 1 FROM users WHERE user_id=?)", (self.__user.id,)) as cur:
                row_exists, = await cur.fetchone()
                self.__is_registered = bool(row_exists)
        return self

    @property
    def is_registered(self) -> bool:
        return self.__is_registered

    @property
    def discord_user(self) -> Optional[User]:
        return self.__user

    @global_operation
    async def get_unverified_users(self) -> AsyncGenerator[UserDetails, None]:
        not_statuses = (UserStatus.VERIFIED.name, UserStatus.DENIED.name)
        async with self.__conn.execute("SELECT * FROM users WHERE status!=? OR status!=?", not_statuses) as cur:
            async for vals in cur:
                yield UserDetails(*vals)

    @global_operation
    async def register(self, user_entry: UserDetails):
        """
        Adds a UserEntry to the database.

        :param user_entry: The UserEntry to add to the database.
        """
        await self.__conn.execute(f"INSERT OR IGNORE INTO users VALUES ({_param_list})", user_entry.to_row())
        if self.__user is not None:
            self.__is_registered = True
        await self.update_images(user_entry.image_urls)

    @user_operation
    async def get_images(self) -> list[str]:
        """
        Gets the images associated with the context User.

        :return: A list of image urls.
        """
        async with self.__conn.execute("SELECT url FROM images WHERE user_ref_id=?", (self.__user.id,)) as cur:
            return [url async for url, in cur]

    @user_operation
    async def delete_images(self):
        """
        Deletes all images associated with the context User.
        """
        await self.__conn.execute("DELETE FROM images WHERE user_ref_id=?", (self.__user.id,))

    @user_operation
    async def update_images(self, image_url_list: list[str]):
        """
        Updates the list of images associated with the context User.

        :param image_url_list: A list of urls to insert into the image table.
        """
        await self.delete_images()
        for url in image_url_list:
            await self.__conn.execute("INSERT OR IGNORE INTO images (user_ref_id, url) VALUES (?, ?)", (self.__user.id, url))

    @user_operation
    async def get_entry(self) -> UserDetails:
        """
        Fetches a the context User's UserEntry from the database.

        :return: Returns a UserEntry with the data of the context User.
        """
        async with self.__conn.execute("SELECT * FROM users WHERE user_id=?", (self.__user.id,)) as cur:
            vals, urls = await cur.fetchone(), await self.get_images()
            return UserDetails(*vals, urls)

    @user_operation
    async def update_entry(self, user_entry: UserDetails):
        """
        Updates the context User's data with a new UserEntry.

        :param user_entry: The UserEntry to update the context User's data with.
        :raises UserMismatchError: Raised if the UserEntry passed does not belong to the context User. i.e. the User ids
        are mismatched.
        """
        if self.__user.id != user_entry.user_id:
            raise UserMismatchError(user_entry, self.__user)
        await self.__conn.execute(
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
            """, (*user_entry.to_row(), user_entry.user_id))
        await self.update_images(user_entry.image_urls)

    @user_operation
    async def unregister(self):
        """
        Removes the context User from the database.
        """
        await self.delete_images()
        await self.__conn.execute("DELETE FROM users WHERE user_id=?", (self.__user.id,))

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.__conn.commit()
        await self.__conn.close()

    def __repr__(self) -> str:
        context = 'Global' if self.__user is None else 'User'
        return f'UserDataManager(context={context}, user={self.__user}, user_registered={self.__is_registered})'


async def is_registered(user: User):
    async with UserEntryManager(user) as _user:
        return _user.is_registered


# async def is_user_registered_with_status(user: User, status_check: ComparableStatus) -> bool:
#     """
#
#     :param user:
#     :param status_check:
#     :return:
#     """
#     async with UserEntryManager(user) as _user:
#         if _user.is_registered:
#             user_entry = await _user.get_entry()
#             return status_check(user_entry.status)
#     return False
