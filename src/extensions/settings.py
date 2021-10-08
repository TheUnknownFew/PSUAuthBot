import discord
from discord.ext import commands
from pydantic import BaseModel


class DiscordSettings(BaseModel):
    auth_token: str
    operating_discord: int
    request_channel: int
    admin_channel: int
    greeter_role: int
    verified_role: int
    new_member_role: int
    command_prefix: str
    activity: str

    @classmethod
    def finalize(cls, bot: commands.Bot):
        if not hasattr(cls, '_bot'):
            cls._bot = bot
            cls.__config__.allow_mutation = False

    @property
    def operating_discord_(self) -> discord.Guild:
        return self._bot.get_guild(self.operating_discord)

    @property
    def request_channel_(self) -> discord.TextChannel:
        return self.operating_discord_.get_channel(self.request_channel)

    @property
    def greeter_role_(self) -> discord.Role:
        return self.operating_discord_.get_role(self.greeter_role)

    @property
    def verified_role_(self) -> discord.Role:
        return self.operating_discord_.get_role(self.verified_role)

    @property
    def new_member_role_(self) -> discord.Role:
        return self.operating_discord_.get_role(self.new_member_role)

    @property
    def admin_channel_(self) -> discord.TextChannel:
        return self.operating_discord_.get_channel(self.admin_channel)


class GoogleSettings(BaseModel):
    email: str
    password: str

    class Config:
        allow_mutation = False


class BotSettings(BaseModel):
    discord: DiscordSettings
    google: GoogleSettings

    def as_tuple(self) -> tuple[DiscordSettings, GoogleSettings]:
        return self.discord, self.google

    class Config:
        allow_mutation = False
