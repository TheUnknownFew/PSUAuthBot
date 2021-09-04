from discord.ext import commands, tasks
import discord

import json
import re

# invite link: https://discord.com/api/oauth2/authorize?client_id=883155763252576258&permissions=134343744&scope=bot


# ----- Setup:

ERR_DELAY = 8
SUCCESS_DELAY = 20

ERR_RESPONSE = discord.Embed(
    title='Missing Information',
    description='Oops! Looks like you are missing an argument.',
    color=discord.Color.red()
)
ERR_RESPONSE.add_field(name='Command', value='`!verify <first name> <last name> <psu email>`', inline=False)
ERR_RESPONSE.add_field(name='Example Usage', value='`!verify john smith jas1234@psu.edu`', inline=False)

SUCCESS_RESPONSE = discord.Embed(
    title='Next Steps',
    description='Almost there! Please complete the following steps.',
    color=discord.Color.green()
)
SUCCESS_RESPONSE.add_field(name='Verify Email', value='• An email has been sent to your Pennstate email.', inline=False)
SUCCESS_RESPONSE.add_field(name='Check your DMs', value='• A DM has been sent to you on Discord outlining final steps and additional information.', inline=False)
SUCCESS_RESPONSE.set_footer(text='If you did not receive an email, or have encountered an issue, please contact an admin.')

with open('config.json') as cfg:
    config = json.load(cfg)
discord_cfg = config['discord']
google_cfg = config['google']

bot = commands.Bot(command_prefix=discord_cfg['command_prefix'], activity=discord.Game(name=discord_cfg['activity']), help_command=None)


# ----- Logic:


def is_command_channel(ctx: commands.Context):
    return ctx.message.channel.id == discord_cfg['request_channel']


@bot.command()
@commands.check(is_command_channel)
async def verify(ctx: commands.Context, first_name: str, last_name: str, email: str):
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
async def missing_param_error(ctx: commands.Context, err):
    if isinstance(err, commands.MissingRequiredArgument):
        await ctx.send(embed=ERR_RESPONSE, delete_after=ERR_DELAY, reference=ctx.message, mention_author=True)
    await ctx.message.delete(delay=ERR_DELAY)


# ----- Main:


def start():
    bot.run(discord_cfg['auth_token'])


if __name__ == '__main__':
    start()
