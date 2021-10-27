import logging

from common.data.settings import discord_cfg as dcfg

from discord.ext import commands
import discord

# invite link: https://discord.com/api/oauth2/authorize?client_id=883155763252576258&permissions=275347926080&scope=bot


# ----- Setup:

bot = commands.Bot(
    command_prefix=dcfg.command_prefix,
    activity=discord.Game(name=dcfg.activity),
    help_command=None
)
dcfg.finalize(bot)

# ----- Main:


def start():
    logging.basicConfig(level=logging.INFO)

    # bot.load_extension('extensions.userdb')
    bot.load_extension('extensions.commands.admin')
    # bot.load_extension('extensions.commands.verify')
    bot.run(dcfg.auth_token)


if __name__ == '__main__':
    start()
