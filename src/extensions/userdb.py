from dataclasses import dataclass, field
from datetime import datetime
from functools import wraps
from types import AsyncGeneratorType
from typing import Union, AsyncGenerator

import aiosqlite as sqlite
from discord import DMChannel, Message, User
from discord.ext import commands

from common.exceptions import UnregisteredUserError, InvalidGlobalOperation, UserMismatchError
from common.bot.userstatus import UserStatus, ComparableStatus
from common.data.settings import discord_cfg as dcfg

_columns: list[str] = ['user_id', 'joined_timestamp', 'first_name', 'last_name',
                       'psu_email', 'status_msg_id', 'dm_channel_id', 'status']
_bot: commands.Bot
_param_list: str = ''.join(['?' for _ in range(len(_columns))])


def setup(bot: commands.Bot):
    global _bot
    _bot = bot


@dataclass
class UserEntry:
    # Discord's internal user id
    user_id: int
    # Time of when user uses !verify command
    joined_timestamp: float
    first_name: str
    last_name: str
    # User's Pennstate Email
    psu_email: str
    # Discord's internal id for the status message sent to the greeters.
    status_msg_id: int
    # Discord's internal id for the User's dm channel.
    dm_channel_id: int
    # Private member used as the string variant of Enum UserStatus.
    # marked as a field so object creation is compatible with reading from the database.
    __status: Union[str, UserStatus] = field()
    # A list of email URLS submitted from the User.
    image_urls: list[str] = field(default_factory=list)

    def __post_init__(self):
        """
        Guarantees that __status will be a UserStatus by converting any incoming strings to a UserStatus.

        :raises KeyError: a KeyError is raised if an invalid UserStatus enum was passed in as a string.
        """
        if isinstance(self.__status, str):
            self.status = UserStatus[self.__status]

    @property
    def status(self) -> UserStatus:
        """
        :return: Returns the User's UserStatus.
        """
        return self.__status

    @status.setter
    def status(self, status: UserStatus):
        """
        Sets the User's UserStatus.

        :param status: A new UserStatus.
        """
        self.__status = status

    @property
    async def user(self) -> User:
        """
        :return: Returns the User's internal discord User.
        """
        return _bot.get_user(self.user_id) or await _bot.fetch_user(self.user_id)

    @property
    async def status_message(self) -> Message:
        """
        :return: Returns the User's status message as a discord internal Message.
        """
        return dcfg.admin_channel_.fetch_message(self.status_msg_id)

    @property
    def dm_channel(self) -> DMChannel:
        """
        :return: Returns the User's direct message channel as a discord internal DMChannel.
        """
        return (await self.user).dm_channel

    @property
    def joined(self) -> datetime:
        """
        :return: Returns the User's join time as a datetime object.
        """
        return datetime.fromtimestamp(self.joined_timestamp)

    def as_tuple(self) -> tuple:
        """
        :return: Returns the User as a tuple object.
        """
        return (self.user_id, self.joined_timestamp, self.first_name, self.last_name,
                self.psu_email, self.status_msg_id, self.dm_channel_id, self.status.name)


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

        :param user_entry:
        :return:
        """
        await self.__con.execute(f"INSERT OR IGNORE INTO users VALUES ({_param_list})", user_entry.as_tuple())
        if self.__user is not None:
            self.__is_registered = True
        await self.update_user_images(user_entry.image_urls)

    @user_operation
    async def get_user_images(self) -> list[str]:
        async with self.__con.execute("SELECT url FROM images WHERE user_ref_id=?", (self.__user.id,)) as cur:
            return [url async for url, in cur]

    @user_operation
    async def delete_user_images(self):
        await self.__con.execute("DELETE FROM images WHERE user_ref_id=?", (self.__user.id,))

    @user_operation
    async def update_user_images(self, image_url_list: list[str]):
        await self.delete_user_images()
        for url in image_url_list:
            await self.__con.execute("INSERT OR IGNORE INTO images (user_ref_id, url) VALUES (?, ?)", (self.__user.id, url))

    @user_operation
    async def get_user_entry(self) -> UserEntry:
        """

        :return:
        """
        async with self.__con.execute("SELECT * FROM users WHERE user_id=?", (self.__user.id,)) as cur:
            vals = await cur.fetchone()
            urls = await self.get_user_images()
            return UserEntry(*vals, urls)

    @user_operation
    async def update_user(self, user_entry: UserEntry):
        """

        :param user_entry:
        :return:
        """
        if self.__user.id != user_entry.user_id:
            raise UserMismatchError(user_entry, self.__user)
        await self.__con.execute(
            """
            UPDATE users
            SET user_id=?,
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

        :return:
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
