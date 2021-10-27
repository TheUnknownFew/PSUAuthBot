from discord.ext import commands

from common.data.embeds import INSTRUCTIONS
from common.data.settings import discord_cfg as dcfg


class AdminCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.__bot: commands.Bot = bot

    @commands.command()
    @commands.has_guild_permissions(administrator=True)
    async def instructions(self, ctx: commands.Context):
        await dcfg.request_channel_.send(embed=INSTRUCTIONS)

    @commands.command(usage='!hello <a> <b>')
    async def hello(self, ctx: commands.Context, a: str, b: int):
        await ctx.send('hello')

    @commands.command()
    async def inspect(self, ctx: commands.Context):
        await ctx.send(f'{self.hello.usage}')


def setup(bot: commands.Bot):
    bot.add_cog(AdminCommands(bot))
