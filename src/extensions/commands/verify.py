from datetime import datetime
from re import match

from discord import Message, DMChannel
from discord.ext import commands, tasks

from common.bot import userstatus, views
from common.bot.verification import VerificationManager
from common.data.userdb import UserEntryManager
from common.exceptions import InvalidEmail, ConfirmationEmailMismatch, UserUpdateError
from common.bot.email import Gmail
from common.bot.userstatus import UserStatus
from common.data.settings import discord_cfg as dcfg
from common.data import embeds as emb, userdb

from extensions.user import UserEntry
from extensions.commands import is_command_channel


class Verify(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.__bot: commands.Bot = bot
        self.__gmail: Gmail = Gmail()
        self.check_for_email_replies.start()

    @commands.Cog.listener(name='on_ready')
    async def register_existing_status_messages(self) -> None:
        if not views.are_status_views_loaded:
            async with UserEntryManager() as users:
                async for user_entry in users.get_unverified_users():
                    views.make_status_view(self.__bot, user_entry)
            views.are_status_views_loaded = True

    @commands.Cog.listener(name='on_message')
    async def if_not_command_then_delete(self, message: Message) -> None:
        """
        Deletes messages in the requests channel that are not extensions.
        :param message: The message sent passed in from the event on_message.
        """
        if self.__bot.user.id != message.author.id:
            ctx: commands.Context = await self.__bot.get_context(message)
            if not ctx.valid and message.channel.id == dcfg.request_channel:
                await message.delete()

    @commands.Cog.listener(name='on_message')
    async def listen_for_canvas_embed(self, message: Message) -> None:
        """
        Listens for user direct messages during the PENDING_BOTH or PENDING_DM status portion of the verification
        process. When a user sends an image or an embed of their canvas home page, the image(s)/embed(s) are sent
        to the user verification status message for admins to manually review.
        :param message: The message sent passed in from the event on_message.
        """
        if self.__bot.user.id != message.author.id and message.guild is None:
            verification_manager = await VerificationManager.from_discord_user(message.author)
            if not verification_manager.is_user_registered:
                return

            img_urls = [att.proxy_url for att in message.attachments if att.content_type.startswith('image')] + \
                       [embed.url for embed in message.embeds if embed.type in ['image', 'gifv', 'link']]
            ctx: commands.Context = await self.__bot.get_context(message)
            if len(img_urls) == 0:
                await ctx.send(embed=emb.IMAGE_NOT_FOUND)
                return
            if verification_manager.accept_canvas_images(img_urls):
                await ctx.send(embed=emb.FINAL_DM)

    @tasks.loop(seconds=dcfg.email_refresh_rate)
    async def check_for_email_replies(self):
        async with UserEntryManager() as users:
            unverified_users = users.get_unverified_users()
            async for user_entry in unverified_users:
                _user = await user_entry.user
                if await userdb.is_user_registered_with_status(_user, userstatus.is_user_pending_email):
                    async with UserEntryManager(_user) as user_manager:
                        email_status = self.__gmail.check_for_replies(user_entry)
                        await email_status(user_entry, user_manager, views.loaded_status_views[user_entry.user_id])

    @commands.group(
        aliases=['v', 'u', 'update'],
        usage='!verify <first name> <last name> <psu email> <confirm email>',
        brief='!verify John Smith jas1234@psu.edu jas1234@psu.edu')
    @commands.check(is_command_channel)
    @commands.guild_only()
    @commands.cooldown(rate=1, per=60, type=commands.BucketType.user)
    async def verify(self, ctx: commands.Context, first_name: str, last_name: str, email: str, confirm_email: str):
        """
        Main command. Starts the verification process for a user. Each parameter is a required parameter of the command.

        This command registers the user into a database and asks the user to provide a canvas image as well as respond
        to an automated email sent to the provided email.
        :param ctx: Passed in by discord.py
        :param first_name: First name of the user.
        :param last_name: Last name of the user.
        :param email: A validly formatted Pennstate Email.
        :param confirm_email: A check against `email` to ensure the user typed in their email correctly.
        """
        if not match('[a-zA-Z]+[0-9]+@psu.edu', email):         # check if valid Pennstate email
            raise InvalidEmail(ctx.author.name, email)
        if email != confirm_email:                              # check if confirmation email matches
            raise ConfirmationEmailMismatch(ctx.author.name, email, confirm_email)

        async with UserEntryManager(ctx.author) as user:
            if not user.__is_registered:
                await ctx.send(embed=emb.NEXT_STEPS, delete_after=emb.SUCCESS_DELAY, reference=ctx.message, mention_author=True)

                dm_channel: DMChannel = await ctx.message.author.create_dm()
                status_message: Message = await dcfg.admin_channel_.send(dcfg.greeter_role_.mention)
                user_entry = UserEntry(ctx.author.id, datetime.now().timestamp(), first_name, last_name, email, status_message.id, dm_channel.id, UserStatus.PENDING_BOTH)

                await dm_channel.send(emb.initial_dm_content(), embed=emb.INITIAL_DM)
                await status_message.edit(embed=await emb.create_status_message(user_entry), view=views.make_status_view(self.__bot, user_entry))
                await user.register_user(user_entry)
                self.__gmail.send_email_to(email)
            else:
                # Todo: 'update' user information embed - tell user to use update
                pass
        await ctx.message.delete(delay=emb.SUCCESS_DELAY)

    @verify.command(
        name='email',
        aliases=['e'],
        usage='!update email <psu email> <confirm email>',
        brief='!update email jas1234@psu.edu jas1234@psu.edu')
    async def update_email(self, ctx: commands.Context, email: str, confirm_email: str):
        async with UserEntryManager(ctx.author) as user:
            if not user.__is_registered:
                raise UserUpdateError(ctx.author)
            if not match('[a-zA-Z]+[0-9]+@psu.edu', email):  # check if valid Pennstate email
                raise InvalidEmail(ctx.author.name, email)
            if email != confirm_email:  # check if confirmation email matches
                raise ConfirmationEmailMismatch(ctx.author.name, email, confirm_email)

            user_entry = await user.get_user_entry()
            if userstatus.is_user_pending_email(user_entry.status):
                self.__gmail.delete_email(email)
                await self.resend(ctx)

    @verify.command(
        name='name',
        aliases=['n'],
        usage='!update name <first name> <last name>',
        brief='!update name John Smith')
    async def update_name(self, ctx: commands.Context, first_name: str, last_name: str):
        async with UserEntryManager(ctx.author) as user:
            if not user.__is_registered:
                raise UserUpdateError(ctx.author)

            user_entry = await user.get_user_entry()
            if user_entry.status <= UserStatus.AWAITING_VERIFICATION:
                user_entry.first_name = first_name
                user_entry.last_name = last_name
                await views.loaded_status_views[user_entry.user_id].update_status_message(new_data=user_entry)

    @commands.command()
    async def resend(self, ctx: commands.Context):
        pass

    @verify.error
    @update_email.error
    @update_name.error
    async def handle_error(self, ctx: commands.Context, err):
        await ctx.message.delete(delay=emb.ERR_DELAY)
        try:
            raise err
        except InvalidEmail as e:
            await ctx.send(embed=emb.invalid_email(e.email), delete_after=emb.ERR_DELAY, reference=ctx.message, mention_author=True)
        except ConfirmationEmailMismatch:
            await ctx.send(embed=emb.EMAIL_MISMATCH, delete_after=emb.ERR_DELAY, reference=ctx.message, mention_author=True)
            self.verify.reset_cooldown(ctx)
        except UserUpdateError:
            await ctx.send("You have not started the verification process yet. Please use the !verify command to start the verification process.")  # todo: fix this embed
        except commands.MissingRequiredArgument:
            await ctx.send(embed=emb.arg_error(ctx.command), delete_after=emb.ERR_DELAY, reference=ctx.message, mention_author=True)
        except commands.CommandOnCooldown as cool_down:
            await ctx.send(embed=emb.on_cooldown(int(cool_down.retry_after)), delete_after=emb.ERR_DELAY, reference=ctx.message, mention_author=True)
        except commands.NoPrivateMessage:
            await ctx.send(embed=emb.not_in_dms(), delete_after=emb.ERR_DELAY)
        finally:
            raise err

    def cog_unload(self) -> None:
        self.check_for_email_replies.cancel()
        self.__gmail.unload()


def setup(bot: commands.Bot):
    bot.add_cog(Verify(bot))
