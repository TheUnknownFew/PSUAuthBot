from typing import Optional

from discord import User

from common.bot import views, userstatus
from common.bot.userstatus import StatusContext, ComparableStatus
from common.bot.views import UserStatusView
from common.data import userdb
from common.data.userdb import UserEntryManager
from extensions.user import UserEntry


class VerificationManager:
    def __init__(self, user_entry: Optional[UserEntry], status_view: Optional[UserStatusView], is_registered: bool):
        self.__user_entry: UserEntry = user_entry
        self.__status_view: UserStatusView = status_view
        self.__is_registered: bool = is_registered

    @property
    def is_user_registered(self) -> bool:
        return self.__is_registered

    @classmethod
    async def from_discord_user(cls, user: User) -> Optional['VerificationManager']:
        async with UserEntryManager(user) as _user:
            if _user.__is_registered:
                return cls(await _user.get_user_entry(), views.loaded_status_views[user.id], _user.__is_registered)
        return cls(None, None, False)

    def accept_canvas_images(self, imgs: list[str]) -> bool:
        if not self.has_status(userstatus.is_user_pending_dm):
            return False
        self.__user_entry.next_status(userstatus.canvas_image_received)
        self.__user_entry.image_urls = imgs
        await self.update()
        return True

    async def has_status(self, status_check: ComparableStatus) -> bool:
        if not self.__is_registered:
            return False
        return await userdb.is_user_registered_with_status(await self.__user_entry.user, status_check)

    async def update(self):
        if self.__is_registered:
            async with UserEntryManager(await self.__user_entry.user) as _user:
                await _user.update_user(self.__user_entry)
            await self.__status_view.update_status_message(new_data=self.__user_entry, display_image=self.__status_view.selected_image())
