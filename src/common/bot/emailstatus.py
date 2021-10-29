from collections import Callable, Awaitable

from common.bot import userstatus
from common.bot.views.statusview import UserStatusView
from common.data import embeds as emb
from common.data.userdb import UserEntryManager
from extensions.user import UserEntry


EmailStatus = Callable[[UserEntry, UserEntryManager, UserStatusView], Awaitable[None]]


async def no_response(user_entry: UserEntry, user: UserEntryManager, view: UserStatusView):
    """
    no response

    :param user_entry:
    :param user:
    :param view:
    :return:
    """
    pass


async def undelivered(user_entry: UserEntry, user: UserEntryManager, view: UserStatusView):
    user_entry.next_status(userstatus.stall_verification)
    await user.update_user(user_entry)
    await view.update_status_message(new_data=user_entry)
    await (await user_entry.dm_channel).send("Looks like the email you supplied us could not be reached. Please use the !update email command.")    #todo: fix this embed


async def valid_reply(user_entry: UserEntry, user: UserEntryManager, view: UserStatusView):
    user_entry.next_status(userstatus.email_received)
    await user.update_user(user_entry)
    await view.update_status_message(new_data=user_entry)


async def timeout(user_entry: UserEntry, user: UserEntryManager, view: UserStatusView):
    await user.remove_user()
    user_entry.next_status(userstatus.user_terminated)
    await (await user_entry.dm_channel).send(embed=emb.email_timeout())
    view.update_user_data(user_entry)
    await view.finalize_verification()
