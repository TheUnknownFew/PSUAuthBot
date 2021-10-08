import discord.ui
from discord.ext import commands

from extensions import userdata
from main import discord_cfg as dcfg
from util.embeds import INSTRUCTIONS_EMBED


class TestSelect(discord.ui.Select['TestView']):
    def __init__(self):
        super().__init__(custom_id='sel1', placeholder='Select Text')
        print([opt.value for opt in self.options])

    async def callback(self, interaction: discord.Interaction):
        self.view.say_hello.label = 'No'
        print('VERY HELLO')


class TestView(discord.ui.View):
    def __init__(self, bot: commands.Bot, msg_id):
        super().__init__(timeout=None)
        self.__bot = bot
        self.__msg_id = msg_id

    async def disable_hello(self):
        print('Hello World')
        # self.__select.add_option(label='Hi', value='1', description='Hello')
        msg = await dcfg.admin_channel_.fetch_message(self.__msg_id)
        await msg.edit(content='Hi', view=self)

    @discord.ui.button(label='Hello', style=discord.ButtonStyle.green, custom_id='b1')
    async def say_hello(self, button: discord.ui.Button, interaction: discord.Interaction):
        print('Hello world', button, interaction)
        await self.disable_hello()

    async def start(self, bot: commands.Bot):
        self.__msg = await dcfg.admin_channel_.send('Hi there', view=self)


class AdminCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.__bot = bot
        self.__is_ready = False

    @commands.Cog.listener(name='on_ready')
    async def ready(self):
        if not self.__is_ready:
            self.__is_ready = True
            self.__bot.add_view(TestView(self.__bot, 888149946480611338), message_id=888149946480611338)

    @commands.command()
    @commands.has_guild_permissions(administrator=True)
    async def instructions(self, ctx: commands.Context):
        await dcfg.request_channel_.send(embed=INSTRUCTIONS_EMBED)

    # @commands.command()
    # @commands.has_guild_permissions(administrator=True)
    # async def test(self, ctx: commands.Context):
    #     view = TestView(ctx)
    #     await view.start(self.__bot)

    @commands.Cog.listener(name='on_test')
    async def t(self, a):
        return a

    @commands.command()
    @commands.has_guild_permissions(administrator=True)
    async def test2(self, ctx: commands.Context):
        self.__bot.dispatch('on_test', 'Hello World')
        a = await self.__bot.wait_for('on_test')
        await ctx.send(a)


def setup(bot: commands.Bot):
    bot.add_cog(AdminCommands(bot))
