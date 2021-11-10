import logging

from common.data.settings import discord_cfg

from discord.ext import commands
import discord

# invite link: https://discord.com/api/oauth2/authorize?client_id=883155763252576258&permissions=275347926080&scope=bot


# ----- Setup:

bot = commands.Bot(
    command_prefix=discord_cfg.command_prefix,
    activity=discord.Game(name=discord_cfg.activity),
    help_command=None
)
discord_cfg.finalize(bot)


# ----- Main:

def start():
    logging.basicConfig(level=logging.INFO)
    bot.load_extension('extensions.loader')
    bot.run(discord_cfg.auth_token)


if __name__ == '__main__':
    start()
