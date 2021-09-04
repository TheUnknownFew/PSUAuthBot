import re

import discord
from discord.ext import commands

from commands.checks import is_command_channel
from staticdata import ERR_DELAY, SUCCESS_DELAY, SUCCESS_RESPONSE, ERR_RESPONSE


class Verify(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.__bot = bot

    @commands.command()
    @commands.check(is_command_channel)
    async def verify(self, ctx: commands.Context, first_name: str, last_name: str, email: str):
        print("Hello ", ctx.message.to_reference())
        if not re.match('[a-zA-Z]+[0-9]+@psu.edu', email):
            invalid_email = discord.Embed(
                title='Invalid Pennstate Email',
                description=f"`{email}` is not a valid Pennstate email.\n "
                            f"Please try again or use `!help verify` for command help.",
                color=discord.Color.red()
            )
            await ctx.send(embed=invalid_email, delete_after=ERR_DELAY, reference=ctx.message, mention_author=True)
            await ctx.message.delete(delay=ERR_DELAY)
            return

        # check if user already executed command
        # if so: reboot the process

        await ctx.send(embed=SUCCESS_RESPONSE, delete_after=SUCCESS_DELAY, reference=ctx.message, mention_author=True)
        await ctx.message.delete(delay=SUCCESS_DELAY)

        # Send email and DM

    @verify.error
    async def missing_param_error(self, ctx: commands.Context, err):
        if isinstance(err, commands.MissingRequiredArgument):
            await ctx.send(embed=ERR_RESPONSE, delete_after=ERR_DELAY, reference=ctx.message, mention_author=True)
        await ctx.message.delete(delay=ERR_DELAY)


def setup(bot: commands.Bot):
    bot.add_cog(Verify(bot))
