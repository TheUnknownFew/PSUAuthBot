from discord.ext import commands

from src.main import discord_cfg


def is_command_channel(ctx: commands.Context):
    return ctx.message.channel.id == discord_cfg.request_channel
