from discord import Guild, TextChannel, Role
from discord.ext import commands
from pydantic import BaseModel


class _DiscordSettings(BaseModel):
    auth_token: str
    operating_discord: int
    request_channel: int
    admin_channel: int
    greeter_role: int
    verified_role: int
    new_member_role: int
    command_prefix: str
    activity: str
    email_response_timeout: int
    email_refresh_rate: float

    @classmethod
    def finalize(cls, bot: commands.Bot):
        if not hasattr(cls, '_bot'):
            cls._bot = bot
            cls.__config__.allow_mutation = False

    @property
    def operating_discord_(self) -> Guild:
        return self._bot.get_guild(self.operating_discord)

    @property
    def request_channel_(self) -> TextChannel:
        return self.operating_discord_.get_channel(self.request_channel)

    @property
    def greeter_role_(self) -> Role:
        return self.operating_discord_.get_role(self.greeter_role)

    @property
    def verified_role_(self) -> Role:
        return self.operating_discord_.get_role(self.verified_role)

    @property
    def new_member_role_(self) -> Role:
        return self.operating_discord_.get_role(self.new_member_role)

    @property
    def admin_channel_(self) -> TextChannel:
        return self.operating_discord_.get_channel(self.admin_channel)


class _GoogleSettings(BaseModel):
    email: str
    password: str

    class Config:
        allow_mutation = False


class _BotSettings(BaseModel):
    discord: _DiscordSettings
    google: _GoogleSettings

    def as_tuple(self) -> tuple[_DiscordSettings, _GoogleSettings]:
        return self.discord, self.google

    class Config:
        allow_mutation = False


discord_cfg, google_cfg = _BotSettings.parse_file('../config.json').as_tuple()
