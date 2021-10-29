from discord import User
from discord.ext import commands

from common.bot.views.statusview import UserStatusView
from extensions.user import UserEntry

are_status_views_loaded: bool = False
loaded_status_views: dict[int, UserStatusView] = {}


def on_view_termination(user: User):
    loaded_status_views.pop(user.id)


def make_status_view(bot: commands.Bot, user_entry: UserEntry) -> UserStatusView:
    if user_entry.user_id in loaded_status_views:
        return loaded_status_views[user_entry.user_id]
    loaded_status_views[user_entry.user_id] = UserStatusView(user_entry, on_view_termination)
    bot.add_view(loaded_status_views[user_entry.user_id], message_id=user_entry.status_msg_id)
    return loaded_status_views[user_entry.user_id]
