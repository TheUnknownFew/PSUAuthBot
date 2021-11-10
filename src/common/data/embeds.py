from datetime import datetime
from typing import Final

from discord import User, Embed, Color
from discord.ext import commands

from common.bot.userstatus import UserStatus
from common.data.user import UserEntry
from common.data.settings import discord_cfg as dcfg

ERR_DELAY: Final = 8
SUCCESS_DELAY: Final = 20

ARG_ERR: Final = Embed(
    title='Missing Information',
    description='Oops! Looks like you are missing an argument.',
    color=Color.red()
).add_field(
    name='Command',
    value='`!verify <first name> <last name> <psu email> <confirm email>`',
    inline=False
).add_field(
    name='Example Usage',
    value='`!verify John Smith jas1234@psu.edu jas1234@psu.edu`',
    inline=False
)

EMAIL_MISMATCH: Final = Embed(
    title='Confirm Email',
    description='Emails do not match. Please try again.',
    color=Color.red()
)

INSTRUCTIONS: Final = Embed(
    title='Welcome to the Discord',
    description='***To Gain Access to this Server:***\n'
                '• Type `!verify <firstname> <lastname> <psu email> <confirm email>` to this channel.\n'
                '• Respond to the Direct Message you will receive.\n'
                '• Respond to the email from **PsuAuthDiscord@gmail.com** sent to your Pennstate email.\n'
                '• Wait for an admin to review and grant you access to the rest of this server.\n\n'
                '***YOU WILL NOT BE ABLE TO SEE THE REST OF THE SERVER UNTIL THESE STEPS ARE FULFILLED***',
    color=Color.blurple()
)

NEXT_STEPS: Final = Embed(
    title='Next Steps',
    description='Almost there! Please complete the following steps.',
    color=Color.green()
).add_field(
    name='Verify Email & Check your DMs',
    value='• An email has been sent to your Pennstate email.\n'
          '• A DM has been sent to you on Discord outlining final steps and additional information.',
    inline=False
).set_footer(text='If you did not receive an email, or have encountered an issue, please contact an admin.')


INITIAL_DM: Final = Embed(
    title='Canvas Verification',
    description='• Please send a single screenshot of your Canvas home page.\n'
                '- The screenshot must display your name and classes as shown on Canvas ***(see example below)***.',
    color=Color.blurple()
).add_field(
    name='Example Image of Canvas:', value='📍'
).set_image(
    url='https://i.imgur.com/WBg5Dv8.png'
).set_author(
    name='PSU Software Discord Verification',
    url='https://discord.gg/22wKkBh3rZ'
)


FINAL_DM: Final = Embed(
    title='Canvas Image(s) Received',
    description='• If you have not already, respond to the email sent to your Pennstate email.\n'
                '• Please make sure to review the rules.\n'
                '• Wait for an admin to grant you access to the rest of the server.\n'
                '• Once verified, make sure your server nickname is accurate. We ask that your nickname remains as'
                'some form of your real name.',
    color=Color.blurple()
).set_footer(text='If you are having any issues, or have any questions, please direct them to an admin.')


ACCESS_GRANTED: Final = Embed(
    title='Access Granted!',
    description='You have been granted access to the rest of the server! Your name in the server has been changed to '
                'your first and last name. Please make sure your server name is accurate. You may also add your major '
                'in #add-major.'  # todo: update this to mention the channel
)


ACCESS_DENIED: Final = Embed(
    title='Access Denied!',
    description='You have been denied access to the server. If you think this is a mistake, please contact an admin.',
    color=Color.red()
)


IMAGE_NOT_FOUND: Final = Embed(
    title='No Image Found',
    description='Oops! The message you just sent did not seem to be an image. '
                'Please send a PNG, JPEG, or a link to an image.',
    color=Color.red()
)


async def create_status_message(user_data: UserEntry, *, image_url: str = None, greeter: User = None) -> Embed:
    user: User = await user_data.user
    embed = Embed(
        title=f'{user_data.first_name} {user_data.last_name} [ {user_data.psu_email} ]',
        description=f'***Discord Username:*** {user.mention} - {user.name}#{user.discriminator}\n'
                    f'***Status:***           {user_data.status!r}',
        timestamp=datetime.now()
    )
    embed.set_thumbnail(url=user.avatar.url)
    footer = ''
    if image_url is not None:
        embed.set_image(url=image_url)
    if greeter is not None:
        if user_data.status == UserStatus.VERIFIED:
            footer += f'Verified by {greeter.display_name} | '
        elif user_data.status == UserStatus.DENIED:
            footer += f'Rejected by {greeter.display_name} | '
    if user_data.status == UserStatus.TERMINATED:
        footer += f'User removed from database | '
    footer += 'last edited'
    embed.set_footer(text=footer)
    return embed


def email_undelivered(provided_email: str):
    return Embed(
        title='Oops! Your email seems to be incorrect.',
        description=f'We tried sending you a verification email to *{provided_email}*, but this email could not be '
                    f'reached. If you believe this is a mistake, please contact a greeter or admin. Otherwise, '
                    f'if that email address is mistakenly wrong, please use `!update email <psu email> <confirm email>` '
                    f'in {dcfg.request_channel_.mention}.',
        color=Color.red()
    )


def invalid_email(email: str) -> Embed:
    return Embed(
        title='Invalid Pennstate Email',
        description=f"`{email}` is not a valid Pennstate email.\n Please try again or use `!help verify` for command help.",
        color=Color.red()
    )


def invalid_canvas_image(requester: User) -> Embed:
    return Embed(
        title='Insufficient Canvas Image:',
        description=f'{requester.mention} has requested that you send a better Canvas image.\n '
                    f'The image was most likely poor in quality or did not show required information.\n\n'
                    f'Please contact them for more clarification.',
        color=Color.yellow()
    )


def on_cooldown(seconds_left: int) -> Embed:
    return Embed(
        title='You are still on cool down',
        description=f'Please try the command again in {seconds_left} seconds',
        color=Color.yellow()
    )


def not_in_dms() -> Embed:
    return Embed(
        title='Cannot process extensions in DMs',
        description=f'Please send extensions to {dcfg.request_channel_.mention} in the ***{dcfg.operating_discord_.name}*** discord.\n '
                    f'Click {dcfg.request_channel_.mention} to continue to that channel.',
        color=Color.red()
    )


def email_timeout() -> Embed:
    return Embed(
        title='Are you there?',
        description=f'We noticed that you have not responded to the verification email within {dcfg.email_refresh_rate} '
                    f'day(s). If you are still interested in accessing ***{dcfg.operating_discord_.name}***, we ask that you'
                    f'restart the verification process by resending the `!verify` command in {dcfg.request_channel_.mention}.\n'
                    f'Click {dcfg.request_channel_.mention} to continue to that channel.',
        color=Color.red()
    )


def initial_dm_content() -> str:
    return '***DISCLAIMER:***\n*By responding to this message with an image attachment ' \
           'or an image url, you acknowledge that admins from **{dcfg.operating_discord_.name}** ' \
           'are able to view said image.\nAttachments you send are apart of the verification process. ' \
           'No other messages sent in this direct message are viewable by admins.*'


def arg_error(command: commands.Command) -> Embed:
    return Embed(
        title='Missing Information',
        description='Oops! Looks like you are missing an argument.',
        color=Color.red()
    ).add_field(
        name='Command',
        value=f'`{command.usage}`',
        inline=False
    ).add_field(
        name='Example Usage',
        value=f'`{command.brief}`',
        inline=False
    )
