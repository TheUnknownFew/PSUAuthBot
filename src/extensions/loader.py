from discord.ext import commands

from extensions.admin import AdminCommands
from extensions.common import CommonListeners
from extensions.verify import DiscordVerification


def setup(bot: commands.Bot):
    bot.add_cog(CommonListeners(bot))
    bot.add_cog(DiscordVerification(bot))
    bot.add_cog(AdminCommands(bot))
