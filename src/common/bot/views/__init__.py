from discord import User
from discord.ext import commands

from common.bot.views.statusview import UserStatusView
from common.data.user import UserEntry

_are_status_views_loaded: bool = False
_loaded_status_views: dict[int, UserStatusView] = {}


def __on_view_termination(user: User):
    _loaded_status_views.pop(user.id)


def make_status_view(bot: commands.Bot, user_entry: UserEntry) -> UserStatusView:
    if user_entry.user_id in _loaded_status_views:
        return _loaded_status_views[user_entry.user_id]
    _loaded_status_views[user_entry.user_id] = UserStatusView(user_entry, __on_view_termination)
    bot.add_view(_loaded_status_views[user_entry.user_id], message_id=user_entry.status_msg_id)
    return _loaded_status_views[user_entry.user_id]


def get_status_view(user_id: int) -> UserStatusView:
    return _loaded_status_views[user_id]


def are_status_views_loaded() -> bool:
    return _are_status_views_loaded
