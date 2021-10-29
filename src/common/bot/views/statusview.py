from collections import Callable
from typing import Optional

import discord
from discord import User, SelectOption, Interaction

from common.bot import userstatus
from common.exceptions import UserMismatchError
from extensions.user import UserEntry
from common.data import embeds as emb
from common.data.settings import discord_cfg as dcfg


class ImageSelect(discord.ui.Select['StatusMessage']):
    def __init__(self):
        super().__init__(custom_id='185s_images', placeholder='No Images Available ...', row=1, disabled=True)
        self.default_option: SelectOption = SelectOption(label='No Images Available', value='None', description='There are no images for this member at this time.')
        self.append_option(self.default_option)
        self.selected_image: Optional[str] = None

    async def callback(self, interaction: Interaction):
        selection = self.values[0]
        for option in self.options:
            if option.value == selection:
                self.placeholder = option.label
                break
        self.selected_image = None if selection == 'None' else selection
        await self.view.update_status_message(display_image=self.selected_image)


class UserStatusView(discord.ui.View):
    def __init__(self, user_data: UserEntry, on_termination: Callable[[User], None]):
        super().__init__(timeout=None)
        self.__user_data: UserEntry = user_data
        self.__image_select: ImageSelect = ImageSelect()
        self.__termination_callback: Callable[[User], None] = on_termination
        self.add_item(self.__image_select)

    def selected_image(self) -> str:
        return self.__image_select.selected_image

    def set_selectable_images(self, images: list[str]) -> None:
        self.__image_select.options.clear()
        if len(images) == 0:
            self.__image_select.append_option(self.__image_select.default_option)
            self.__image_select.placeholder = 'No Images Available ...'
            self.__image_select.disabled = True
            return
        self.__image_select.add_option(label='Select an Image', value='None')
        for i, url in enumerate(images):
            self.__image_select.add_option(label=f'Canvas Image {i + 1}', value=url, emoji='\U0001F4CE')
        self.__image_select.disabled = False
        self.__image_select.placeholder = 'New Image(s) Available ...'

    def update_user_data(self, user_entry: UserEntry):
        if user_entry.user_id != self.__user_data.user_id:
            raise UserMismatchError(user_entry, self.__user_data)
        self.__user_data = user_entry
        self.set_selectable_images(self.__user_data.image_urls)

    async def update_status_message(self, *, new_data: UserEntry = None, display_image: str = None, greeter: User = None):
        """
        Edits the Status message belonging to `self.__user_data`:

        - If `new_data` is provided, user information in the status message will be updated.
        - If `display_image` is provided, an image selected from the select dropdown will be embedded into the display message.
        - If `display_image` is None, then there will be no embedded image in the updated status message.

        :param new_data: Updates user's status message with updated fields from new_data.
        :param display_image: The url of the image to embed in the status message.
        :param greeter: The greeter who interacted with the status message.
        :raises UserMismatchError: Raised if `new_data` does not refer to the same user as `self.__user_data`.
        """
        if new_data is not None:
            self.update_user_data(new_data)
        status_message = await self.__user_data.status_message
        updated_embed = await emb.create_status_message(self.__user_data, image_url=display_image, greeter=greeter)
        await status_message.edit(embed=updated_embed, view=self)

    async def finalize_verification(self, greeter: User = None) -> None:
        self.grant_verification_access.disabled = True
        self.deny_verification_access.disabled = True
        self.request_canvas_image.disabled = True
        self.__image_select.disabled = True
        await self.update_status_message(greeter=greeter)
        self.__termination_callback(await self.__user_data.user)
        self.stop()

    @discord.ui.button(label='Verify', style=discord.ButtonStyle.green, custom_id='185b_verify', row=0, emoji='\U00002714')
    async def grant_verification_access(self, _: discord.ui.Button, interaction: Interaction):
        self.__user_data.next_status(userstatus.user_verified)
        user = await dcfg.operating_discord_.fetch_member(self.__user_data.user_id)
        dm_channel = await self.__user_data.dm_channel
        await user.remove_roles(dcfg.new_member_role_, reason='User verified')
        await user.add_roles(dcfg.verified_role_, reason='User verified')
        await user.edit(nick=f'{self.__user_data.first_name} {self.__user_data.last_name}', reason='Ensure user`s name follows server naming rules')
        await dm_channel.send(embed=emb.ACCESS_GRANTED)
        await self.finalize_verification(interaction.user)

    @discord.ui.button(label='Deny', style=discord.ButtonStyle.red, custom_id='185b_deny', row=0, emoji='\U0000274C')
    async def deny_verification_access(self, _: discord.ui.Button, interaction: Interaction):
        self.__user_data.next_status(userstatus.user_denied)
        dm_channel = await self.__user_data.dm_channel
        await dm_channel.send(embed=emb.ACCESS_DENIED)
        await self.finalize_verification(interaction.user)

    @discord.ui.button(label='Request New Canvas Image', style=discord.ButtonStyle.blurple, custom_id='185b_canvas', row=0, emoji='\U000026A0')
    async def request_canvas_image(self, _: discord.ui.Button, interaction: Interaction):
        self.__user_data.next_status(userstatus.canvas_image_requested)
        dm_channel = await self.__user_data.dm_channel
        await dm_channel.send(embed=emb.invalid_canvas_image(interaction.user))
