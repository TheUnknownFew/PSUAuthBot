from collections.abc import Callable, Awaitable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from discord import User, Message, DMChannel
from discord.ext import commands

from common.bot.userstatus import UserStatus
from common.data.settings import discord_cfg
from common.data.userdb import UserEntryManager
from common.data.userdetails import UserDetails

UserInitializationCallback = Callable[[commands.Context], Awaitable[tuple[int, int]]]


@dataclass
class UserEntry:
    user_details: UserDetails
    bot: Optional[commands.Bot] = field(default=None, kw_only=True)
    partially_initialized: bool = field(default=False, kw_only=True)
    is_registered: bool = field(default=False, kw_only=True)

    @property
    def user_id(self) -> int:
        return self.user_details.user_id

    @property
    async def user(self) -> User:
        """
        :return: Returns the User's internal discord User.
        """
        return self.bot.get_user(self.user_id) or await self.bot.fetch_user(self.user_id)

    @property
    def joined(self) -> datetime:
        """
        :return: Returns the User's join time as a datetime object.
        """
        return datetime.fromtimestamp(self.user_details.joined_timestamp)

    @property
    def first_name(self) -> str:
        return self.user_details.first_name

    @property
    def last_name(self) -> str:
        return self.user_details.last_name

    @property
    def psu_email(self) -> str:
        return self.user_details.psu_email

    @property
    def status_message_id(self) -> int:
        return self.user_details.status_msg_id

    @property
    async def status_message(self) -> Message:
        """
        :return: Returns the User's status message as a discord internal Message.
        """
        return await discord_cfg.admin_channel_.fetch_message(self.status_message_id)

    @property
    def dm_channel_id(self) -> int:
        return self.user_details.dm_channel_id

    @property
    async def dm_channel(self) -> DMChannel:
        """
        :return: Returns the User's direct message channel as a discord internal DMChannel.
        """
        return (await self.user).dm_channel

    @property
    def status(self) -> UserStatus:
        return UserStatus[self.user_details.status]

    @status.setter
    def status(self, status: UserStatus):
        self.user_details.status = status.name

    @property
    def image_urls(self) -> list[str]:
        return self.user_details.image_urls

    @classmethod
    async def from_user(cls, user: User, bot: commands.Bot = None) -> Optional['UserEntry']:
        async with UserEntryManager(user) as _user:
            if _user.is_registered:
                return cls(await _user.get_entry(), bot=bot, is_registered=True)
        return None

    @classmethod
    async def new_user(cls, ctx: commands.Context, first_name: str, last_name: str, email: str, callback: UserInitializationCallback):
        if user_exists := cls.from_user(ctx.author, ctx.bot):
            return user_exists

        status_message, dm_channel = await callback(ctx)

