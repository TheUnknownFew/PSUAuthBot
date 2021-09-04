import discord

ERR_DELAY = 8
SUCCESS_DELAY = 20

ERR_RESPONSE = discord.Embed(
    title='Missing Information',
    description='Oops! Looks like you are missing an argument.',
    color=discord.Color.red()
)
ERR_RESPONSE.add_field(name='Command', value='`!verify <first name> <last name> <psu email>`', inline=False)
ERR_RESPONSE.add_field(name='Example Usage', value='`!verify john smith jas1234@psu.edu`', inline=False)

SUCCESS_RESPONSE = discord.Embed(
    title='Next Steps',
    description='Almost there! Please complete the following steps.',
    color=discord.Color.green()
)
SUCCESS_RESPONSE.add_field(name='Verify Email', value='• An email has been sent to your Pennstate email.', inline=False)
SUCCESS_RESPONSE.add_field(name='Check your DMs', value='• A DM has been sent to you on Discord outlining final steps and additional information.', inline=False)
SUCCESS_RESPONSE.set_footer(text='If you did not receive an email, or have encountered an issue, please contact an admin.')
