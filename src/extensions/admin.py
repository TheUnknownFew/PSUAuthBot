from dataclasses import dataclass

from discord.ext import commands
from discord.ext.commands import Greedy

from common.data.embeds import INSTRUCTIONS
from common.data.settings import discord_cfg as dcfg


class A:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.tot = x + y

    @classmethod
    async def convert(cls, ctx, x):
        Greedy
        print('Hello:', x)
        return cls(1, 1)


class AdminCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.__bot: commands.Bot = bot

    @commands.command()
    @commands.has_guild_permissions(administrator=True)
    async def instructions(self, ctx: commands.Context):
        await dcfg.request_channel_.send(embed=INSTRUCTIONS)

    @commands.command()
    async def test(self, ctx: commands.Context, args: A):
        print(args.tot)

    @commands.command(usage='!hello <a> <b>')
    async def hello(self, ctx: commands.Context, a: str, b: int):
        await ctx.send('hello')

    @commands.command()
    async def inspect(self, ctx: commands.Context):
        await ctx.send(f'{self.hello.usage}')
