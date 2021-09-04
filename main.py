from discord.ext import commands, tasks
import discord

import json

# invite link: https://discord.com/api/oauth2/authorize?client_id=883155763252576258&permissions=134343744&scope=bot


# ----- Setup:


with open('config.json') as cfg:
    config = json.load(cfg)
discord_cfg = config['discord']
google_cfg = config['google']

bot = commands.Bot(command_prefix=discord_cfg['command_prefix'], activity=discord.Game(name=discord_cfg['activity']), help_command=None)


# ----- Main:


def start():
    bot.load_extension('commands.verify')
    bot.run(discord_cfg['auth_token'])


if __name__ == '__main__':
    start()
