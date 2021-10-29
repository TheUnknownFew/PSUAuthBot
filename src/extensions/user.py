from dataclasses import dataclass, field
from datetime import datetime
from typing import Union, Optional, Any

from discord import DMChannel, Message, User
from discord.ext import commands

from common.bot.userstatus import UserStatus, StatusContext
from common.data.settings import discord_cfg as dcfg

_bot: commands.Bot


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
        return await dcfg.admin_channel_.fetch_message(self.status_msg_id)

    @property
    async def dm_channel(self) -> DMChannel:
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

    def next_status(self, status_context: StatusContext):
        self.status = status_context(self.status)
