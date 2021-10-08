from re import match
from typing import Callable, Optional

import discord
from discord.ext import commands, tasks

from extensions import userdata as ud
from extensions.checks import is_command_channel
from main import discord_cfg as dcfg
from util import embeds as emb
from util.botexceptions import UserMismatchError
from util.email import Gmail


class ImageSelect(discord.ui.Select['StatusMessage']):
    def __init__(self):
        super().__init__(custom_id='185s_images', placeholder='No Images Available ...', row=1, disabled=True)
        self.default_option = discord.SelectOption(label='No Images Available', value='None', description='There are no images for this member at this time.')
        self.append_option(self.default_option)

    async def callback(self, interaction: discord.Interaction):
        selection = self.values[0]
        for option in self.options:
            if option.value == selection:
                self.placeholder = option.label
                break
        await self.view.update_status_message(display_image=None if selection == 'None' else selection)


class StatusMessage(discord.ui.View):
    def __init__(self, user_data: ud.UserData, on_termination: Callable[[ud.User], None]):
        super().__init__(timeout=None)
        self.__user_data: ud.UserData = user_data
        self.__image_select: ImageSelect = ImageSelect()
        self.__termination_callback: Callable[[ud.User], None] = on_termination
        self.add_item(self.__image_select)

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

    async def update_status_message(self, *, new_data: ud.UserData = None, display_image: str = None, greeter: ud.User = None):
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
        if new_data is not None and new_data.user_id != self.__user_data.user_id:
            raise UserMismatchError(new_data, self.__user_data)
        if new_data is not None:
            self.__user_data = new_data
            self.set_selectable_images(self.__user_data.image_urls)
        status_message = await self.__user_data.status_message
        updated_embed = await emb.create_status_embed(self.__user_data, image_url=display_image, greeter=greeter)
        await status_message.edit(embed=updated_embed, view=self)

    async def finalize_verification(self, greeter: ud.User) -> None:
        self.grant_verification_access.disabled = True
        self.deny_verification_access.disabled = True
        self.request_canvas_image.disabled = True
        self.__image_select.disabled = True
        await self.update_status_message(greeter=greeter)
        self.__termination_callback(await self.__user_data.user)
        self.stop()

    @discord.ui.button(label='Verify', style=discord.ButtonStyle.green, custom_id='185b_verify', row=0, emoji='\U00002714')
    async def grant_verification_access(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.__user_data.status = ud.Status.VERIFIED
        user = await dcfg.operating_discord_.fetch_member(self.__user_data.user_id)
        dm_channel = await self.__user_data.dm_channel
        await user.remove_roles(dcfg.new_member_role_, reason='User verified')
        await user.add_roles(dcfg.verified_role_, reason='User verified')
        await user.edit(nick=f'{self.__user_data.first_name} {self.__user_data.last_name}', reason='Ensure user`s name follows server naming rules')
        await dm_channel.send(embed=emb.ACCESS_GRANTED_EMBED)
        await self.finalize_verification(interaction.user)

    @discord.ui.button(label='Deny', style=discord.ButtonStyle.red, custom_id='185b_deny', row=0, emoji='\U0000274C')
    async def deny_verification_access(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.__user_data.status = ud.Status.DENIED
        dm_channel = await self.__user_data.dm_channel
        await dm_channel.send(embed=emb.ACCESS_DENIED_EMBED)
        await self.finalize_verification(interaction.user)

    @discord.ui.button(label='Request New Canvas Image', style=discord.ButtonStyle.blurple, custom_id='185b_canvas', row=0, emoji='\U000026A0')
    async def request_canvas_image(self, button: discord.ui.Button, interaction: discord.Interaction):
        if self.__user_data.status == ud.Status.AWAITING_VERIFICATION:
            self.__user_data.status = ud.Status.PENDING_DM
        elif self.__user_data.status == ud.Status.PENDING_EMAIL:
            self.__user_data.status = ud.Status.PENDING_BOTH
        dm_channel = await self.__user_data.dm_channel
        await dm_channel.send(embed=emb.canvas_image_embed(interaction.user))


class Verify(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.__bot: commands.Bot = bot
        self.__gmail: Gmail = Gmail()
        self.__are_status_views_loaded = False
        self.__loaded_status_views: dict[int, StatusMessage] = {}
        self.check_for_email_replies.start()

    def __on_view_termination(self, user: ud.User):
        self.__loaded_status_views.pop(user.id)

    def __make_status_view(self, user_data: ud.UserData) -> StatusMessage:
        self.__loaded_status_views[user_data.user_id] = StatusMessage(user_data, self.__on_view_termination)
        self.__bot.add_view(self.__loaded_status_views[user_data.user_id], message_id=user_data.status_msg_id)
        return self.__loaded_status_views[user_data.user_id]

    @commands.Cog.listener(name='on_ready')
    async def register_existing_status_messages(self) -> None:
        if not self.__are_status_views_loaded:
            async with ud.UserDataManager() as users:
                async for user_data in users.get_unverified_users():
                    self.__make_status_view(user_data)
            self.__are_status_views_loaded = True

    @commands.Cog.listener(name='on_message')
    async def if_not_command_then_delete(self, message: discord.Message) -> None:
        """
        Deletes messages in the requests channel that are not extensions.
        :param message: The message sent passed in from the event on_message.
        """
        if self.__bot.user.id != message.author.id:
            ctx: commands.Context = await self.__bot.get_context(message)
            if not ctx.valid and message.channel.id == dcfg.request_channel:
                await message.delete()

    @commands.Cog.listener(name='on_message')
    async def listen_for_canvas_embed(self, message: discord.Message) -> None:
        """
        Listens for user direct messages during the PENDING_BOTH or PENDING_DM status portion of the verification
        process. When a user sends an image or an embed of their canvas home page, the image(s)/embed(s) are sent
        to the user verification status message for admins to manually review.
        :param message: The message sent passed in from the event on_message.
        """
        if self.__bot.user.id != message.author.id:
            ctx: commands.Context = await self.__bot.get_context(message)
            has_status = await ud.is_user_registered_with_status(
                message.author, lambda current_status: current_status < ud.Status.PENDING_EMAIL
            )
            if message.guild is None and has_status:
                img_urls = [att.proxy_url for att in message.attachments if att.content_type.startswith('image')] + \
                           [embed.url for embed in message.embeds if embed.type in ['image', 'gifv', 'link']]
                if len(img_urls) == 0:
                    await ctx.send(embed=emb.IMAGE_NOT_FOUND)
                    return
                async with ud.UserDataManager(ctx.author) as user:
                    user_data = await user.get_user_data()
                    if user_data.status == ud.Status.PENDING_BOTH:
                        user_data.status = ud.Status.PENDING_EMAIL
                    else:
                        user_data.status = ud.Status.AWAITING_VERIFICATION
                    user_data.image_urls = img_urls
                    await user.update_user(user_data)
                await self.__loaded_status_views[user_data.user_id].update_status_message(new_data=user_data)
                await ctx.send(embed=emb.FINAL_DM_EMBED)

    @tasks.loop(seconds=20.0)
    async def check_for_email_replies(self):
        async with ud.UserDataManager() as users:
            from_emails: list[ud.UserData] = []
            async for _user in users.get_unverified_users():
                user = await _user.user
                if await ud.is_user_registered_with_status(user, lambda s: s == ud.Status.PENDING_BOTH or s == ud.Status.PENDING_EMAIL):
                    from_emails.append(_user)
            if len(from_emails) > 0:
                self.__gmail.check_for_replies(from_emails)
                # for email, has_response in zip(from_emails, self.__gmail.check_for_replies(from_emails)):
                #     pass

    # @check_for_email_replies.error
    # async def tmp_error(self, exception):
    #     self.check_for_email_replies.restart()

    @commands.command()
    @commands.check(is_command_channel)
    @commands.guild_only()
    @commands.cooldown(rate=1, per=60, type=commands.BucketType.user)
    async def verify(self, ctx: commands.Context, first_name: str, last_name: str, email: str, confirm_email: str):
        """

        :param ctx:
        :param first_name:
        :param last_name:
        :param email:
        :param confirm_email:
        """
        # check if valid Pennstate email
        # Todo: uncomment this. commented during debug
        # if not match('[a-zA-Z]+[0-9]+@psu.edu', email):
        #     await ctx.send(embed=emb.invalid_email_embed(email), delete_after=emb.ERR_DELAY, reference=ctx.message, mention_author=True)
        #     await ctx.message.delete(delay=emb.ERR_DELAY)
        #     return

        # check if confirmation email matches
        if email != confirm_email:
            await ctx.send(embed=emb.EMAIL_MISMATCH_EMBED, delete_after=emb.ERR_DELAY, reference=ctx.message, mention_author=True)
            await ctx.message.delete(delay=emb.ERR_DELAY)
            self.verify.reset_cooldown(ctx)
            return

        async with ud.UserDataManager(ctx.author) as user:
            if not user.is_registered:
                # Response: Sending email . . .
                # if email undelivered
                #   stop, try again
                # Response: Email sent
                #   register user
                #   listen for reply
                await ctx.send(embed=emb.SUCCESS_EMBED, delete_after=emb.SUCCESS_DELAY, reference=ctx.message, mention_author=True)
                dm_channel: discord.DMChannel = await ctx.message.author.create_dm()
                await dm_channel.send(
                    f'***DISCLAIMER:***\n*By responding to this message with an image attachment or an image url, you '
                    f'acknowledge that admins from **{dcfg.operating_discord_.name}** '
                    f'are able to view said image.\nAttachments you send are apart of the verification process. No other '
                    f'messages sent in this direct message are viewable by admins.*',
                    embed=emb.INITIAL_DM_EMBED
                )
                status_message: discord.Message = await dcfg.admin_channel_.send(dcfg.greeter_role_.mention)
                user_data = ud.UserData(ctx.author.id, first_name, last_name, email, status_message.id, dm_channel.id, ud.Status.PENDING_BOTH)
                await status_message.edit(embed=await emb.create_status_embed(user_data), view=self.__make_status_view(user_data))
                await user.register_user(user_data)
                self.__gmail.send_email_to(email)
            else:
                # Todo: 'update' user information embed - tell user to use update
                pass
        await ctx.message.delete(delay=emb.SUCCESS_DELAY)

    # @commands.command()
    # @commands.check(is_command_channel)
    # @commands.guild_only()
    # # @commands.cooldown(rate=1, per=60, type=commands.BucketType.user)
    # async def update(self, first_name: str, last_name: str, email: Optional[str] = None):
    #     # Todo: 'update' user information command
    #     pass
    #
    # @commands.command()
    # @commands.check(is_command_channel)
    # @commands.guild_only()
    # # @commands.cooldown(rate=1, per=60, type=commands.BucketType.user)
    # async def resend(self, ctx: commands.Context):
    #     # self.query_user('atc17@psu.edu')
    #     print(type(ctx.author.id))

    @verify.error
    # @resend.error
    async def handle_error(self, ctx: commands.Context, err):
        await ctx.message.delete(delay=emb.ERR_DELAY)
        try:
            raise err
        except commands.MissingRequiredArgument:
            await ctx.send(embed=emb.ARG_ERR_EMBED, delete_after=emb.ERR_DELAY, reference=ctx.message, mention_author=True)
        except commands.CommandOnCooldown as cool_down:
            await ctx.send(embed=emb.cool_down_embed(int(cool_down.retry_after)), delete_after=emb.ERR_DELAY, reference=ctx.message, mention_author=True)
        except commands.NoPrivateMessage:
            await ctx.send(embed=emb.not_in_dms_embed(), delete_after=emb.ERR_DELAY)
        finally:
            raise err

    def cog_unload(self) -> None:
        self.check_for_email_replies.cancel()
        self.__gmail.unload()


def setup(bot: commands.Bot):
    bot.add_cog(Verify(bot))
