import logging
from extensions.settings import DiscordSettings, BotSettings

from discord.ext import commands
import discord

# invite link: https://discord.com/api/oauth2/authorize?client_id=883155763252576258&permissions=275347926080&scope=bot


# ----- Setup:

discord_cfg, google_cfg = BotSettings.parse_file('../config.json').as_tuple()

bot = commands.Bot(
    command_prefix=discord_cfg.command_prefix,
    activity=discord.Game(name=discord_cfg.activity),
    help_command=None,
)

discord_cfg.finalize(bot)

# ----- Main:


def start():
    logging.basicConfig(level=logging.INFO)

    bot.load_extension('extensions.userdata')
    # bot.load_extension('extensions.email')
    # # bot.load_extension('extensions.commands.admin')
    bot.load_extension('extensions.commands.verify')
    bot.run(discord_cfg.auth_token)


if __name__ == '__main__':
    start()
