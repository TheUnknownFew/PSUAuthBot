from dataclasses import dataclass
from functools import wraps
from types import AsyncGeneratorType
from typing import Union, Callable, AsyncGenerator

import aiosqlite as sqlite
import discord
from discord.ext import commands

from main import discord_cfg
from util import OrderedEnum
from util.botexceptions import UnregisteredUserError, UserMismatchError, InvalidGlobalOperation

User = Union[discord.User, discord.Member]

_columns: list[str] = ['user_id', 'first_name', 'last_name', 'psu_email', 'status_msg_id', 'dm_channel_id', 'status']
_bot: commands.Bot


def setup(bot: commands.Bot):
    global _bot
    _bot = bot


class Status(OrderedEnum):
    # Order of status matters.
    ATTEMPTED = (1, '\U000026A0 Attempted')                                         # user already tried !verify
    PENDING_BOTH = (2, '\U00002709 \U0001F4CE Awaiting Email & Canvas Image')       # waiting for the user to respond to DMs and email
    PENDING_DM = (3, '\U0001F4CE Awaiting Canvas Image')                            # waiting for the user to respond to DMs
    PENDING_EMAIL = (4, '\U00002709 Awaiting Email')                                # waiting for the user to respond to email
    AWAITING_VERIFICATION = (5, '\U0001F510 Awaiting Verification')                 # waiting admin to verify user
    VERIFIED = (6, '\U00002714 Verified')                                           # user has been verified by admin
    DENIED = (7, '\U0000274C Rejected')                                             # user was denied from the verification process.

    def __init__(self, int_val: int, representation: str):
        self._value_ = int_val
        self.representation: str = representation

    def __repr__(self):
        return self.representation


@dataclass
class UserData:
    user_id: int
    first_name: str
    last_name: str
    psu_email: str
    status_msg_id: int
    dm_channel_id: int
    __status: str
    image_urls: list[str]

    def __init__(
            self,
            user_id: int,
            first_name: str,
            last_name: str,
            psu_email: str,
            status_msg_id: int,
            dm_channel_id: int,
            status: Union[str, Status],
            image_urls=None
    ):
        if image_urls is None:
            image_urls = []
        self.user_id = user_id
        self.first_name = first_name
        self.last_name = last_name
        self.psu_email = psu_email
        self.status_msg_id = status_msg_id
        self.dm_channel_id = dm_channel_id
        self.__status = status.name if isinstance(status, Status) else status
        self.image_urls = image_urls

    @property
    async def user(self) -> User:
        return await _bot.fetch_user(self.user_id)

    @property
    async def status_message(self) -> discord.Message:
        return await discord_cfg.admin_channel_.fetch_message(self.status_msg_id)

    @property
    async def dm_channel(self) -> discord.DMChannel:
        return (await self.user).dm_channel

    @property
    def status(self) -> Status:
        return Status[self.__status]

    @status.setter
    def status(self, new_status: Status):
        self.__status = new_status.name

    def as_db_item(self) -> tuple:
        return (
            self.user_id,
            self.first_name,
            self.last_name,
            self.psu_email,
            self.status_msg_id,
            self.dm_channel_id,
            self.__status
        )


def user_operation(coro):
    @wraps(coro)
    def wrapper(*args, **kwargs):
        self: UserDataManager = args[0]
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


class UserDataManager:
    def __init__(self, user: User = None):
        """
        Database connection manager used for managing user data:\n
        Contexts - Global, User

        **Global:** Specified if no user was passed to `__init__` \n
        A global context can be used when a user is not required to fetch data from the database.
        A global context is less restrictive than a User context.

        **User:** Specified if a discord user was passed to `__init__` \n
        A user context must be used in order to fetch data about a specific user.

        :param user: A discord user or None. Some operations cannot be executed if user is None.
        """
        self.__user: User = user
        self.__is_registered: bool = False
        self.__con: sqlite.Connection

    async def __aenter__(self):
        """

        :return:
        """
        self.__con = await sqlite.connect('../user_data.db')
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
    async def get_unverified_users(self) -> AsyncGenerator[UserData, None]:
        not_statuses = (Status.VERIFIED.name, Status.DENIED.name)
        async with self.__con.execute("SELECT * FROM users WHERE status!=? OR status!=?", not_statuses) as cur:
            async for vals in cur:
                yield UserData(*vals)

    @global_operation
    async def register_user(self, user_data: UserData):
        """

        :param user_data:
        :return:
        """
        await self.__con.execute("INSERT OR IGNORE INTO users VALUES (?, ?, ?, ?, ?, ?, ?)", user_data.as_db_item())
        if self.__user is not None:
            self.__is_registered = True
        await self.update_user_images(user_data.image_urls)

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
    async def get_user_data(self) -> UserData:
        """

        :return:
        """
        async with self.__con.execute("SELECT * FROM users WHERE user_id=?", (self.__user.id,)) as cur:
            vals = await cur.fetchone()
            urls = await self.get_user_images()
            return UserData(*vals, urls)

    @user_operation
    async def update_user(self, user_data: UserData):
        """

        :param user_data:
        :return:
        """
        if self.__user.id != user_data.user_id:
            raise UserMismatchError(user_data, self.__user)
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
            """, (*user_data.as_db_item(), user_data.user_id))
        await self.update_user_images(user_data.image_urls)

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.__con.commit()
        await self.__con.close()

    def __repr__(self) -> str:
        context = 'Global' if self.__user is None else 'User'
        return f'UserDataManager(context={context}, user={self.__user}, user_registered={self.__is_registered})'


async def is_user_registered_with_status(user: User, status_check: Callable[[Status], bool]) -> bool:
    """

    :param user:
    :param status_check:
    :return:
    """
    async with UserDataManager(user) as _user:
        if _user.is_registered:
            user_data = await _user.get_user_data()
            return status_check(user_data.status)
    return False
