from discord import Message
from discord.ext import commands

from common.bot import views
from common.data.settings import discord_cfg
from common.data._userdb import UserEntryManager


class CommonListeners(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.__bot: commands.Bot = bot

    @commands.Cog.listener(name='on_ready')
    async def reconnect_status_views(self) -> None:
        """
        Valid status views that have been established on previous runtime sessions of the bot are re-established here
        so that the bot can maintain them during its current runtime.
        """
        if not views.are_status_views_loaded():
            async with UserEntryManager() as users:
                async for user_entry in users.get_unverified_users():
                    views.make_status_view(self.__bot, user_entry)
            views._are_status_views_loaded = True

    @commands.Cog.listener(name='on_message')
    async def allow_only_commands(self, message: Message) -> None:
        """
        Any message sent to the commands channel defined in the discord config that is not a command is deleted by this
        function.
        :param message: The message sent, passed in from the event on_message.
        """
        if self.__bot.user.id != message.author.id:
            ctx: commands.Context = await self.__bot.get_context(message)
            if not ctx.valid and message.channel.id == discord_cfg.request_channel:
                await message.delete()
