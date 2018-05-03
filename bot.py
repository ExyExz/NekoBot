from discord.ext import commands
import logging, traceback, sys, discord
from datetime import date
from collections import Counter
import datetime
import aiohttp
import random, asyncio
import config
log = logging.getLogger('NekoBot')
log.setLevel(logging.INFO)
date = f"{date.today().timetuple()[0]}_{date.today().timetuple()[1]}_{date.today().timetuple()[2]}"
handler = logging.FileHandler(filename=f'NekoBot_{date}.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
log.addHandler(handler)

startup_extensions = {
    'modules.audio',
    'modules.cardgame',
    'modules.chatbot',
    'modules.discordbots',
    'modules.donator',
    'modules.eco',
    'modules.fun',
    'modules.games',
    'modules.general',
    'modules.imgwelcome',
    'modules.marriage',
    'modules.mod',
    'modules.nsfw',
    'modules.reactions'
}

def _prefix_callable(bot, msg):
    prefixes = ['n!', 'N!']
    return commands.when_mentioned_or(*prefixes)(bot, msg)

class NekoBot(commands.AutoShardedBot):

    def __init__(self):
        super().__init__(command_prefix=_prefix_callable, #commands.when_mentioned_or('n!')
                         description="NekoBot",
                         pm_help=None,
                         shard_id=0,
                         status=discord.Status.dnd,
                         max_messages=5000,
                         help_attrs={'hidden': True})
        self.counter = Counter()
        for extension in startup_extensions:
            try:
                self.load_extension(extension)
            except:
                print("Failed to load {}.".format(extension), file=sys.stderr)
                traceback.print_exc()

    async def send_cmd_help(self, ctx):
        if ctx.invoked_subcommand:
            pages = await self.formatter.format_help_for(ctx, ctx.invoked_subcommand)
            for page in pages:
                await ctx.send(page)
        else:
            pages = await self.formatter.format_help_for(ctx, ctx.command)
            for page in pages:
                await ctx.send(page)

    async def on_command_error(self, ctx, exception):
        channel = self.get_channel(431987399581499403)
        if str(exception) == "Command raised an exception: NotFound: NOT FOUND (status code: 404): Unknown Channel":
            return
        if isinstance(exception, commands.NoPrivateMessage):
            return
        elif isinstance(exception, commands.DisabledCommand):
            return
        elif isinstance(exception, discord.Forbidden):
            return
        elif isinstance(exception, discord.NotFound):
            return
        elif isinstance(exception, commands.CommandInvokeError):
            em = discord.Embed(color=0xDEADBF,
                               title="Error",
                               description=f"Error in command {ctx.command.qualified_name}, "
                                           f"[Support Server](https://discord.gg/q98qeYN)")
            await channel.send(embed=discord.Embed(color=0xff6f3f,
                                                   title="Command Error").add_field(
                name=f"Command: {ctx.command.qualified_name}",
                value=f"```py\n{exception}```"))
            await ctx.send(embed=em)
            print('In {}:'.format(ctx.command.qualified_name), file=sys.stderr)
            traceback.print_tb(exception.original.__traceback__)
            print('{}: {}'.format(exception.original.__class__.__name__, exception.original), file=sys.stderr)
        elif isinstance(exception, commands.BadArgument):
            await self.send_cmd_help(ctx)
        elif isinstance(exception, commands.MissingRequiredArgument):
            await self.send_cmd_help(ctx)
        elif isinstance(exception, commands.CheckFailure):
            await ctx.send('You are not allowed to use that command.', delete_after=5)
        elif isinstance(exception, commands.CommandOnCooldown):
            await ctx.send('Command is on cooldown... {:.2f}s left'.format(exception.retry_after), delete_after=5)
        elif isinstance(exception, commands.CommandNotFound):
            return
        else:
            log.exception(type(exception).__name__, exc_info=exception)
            await channel.send(embed=discord.Embed(color=0xff6f3f, title="Unknown Error", description=f"{exception}"))

    async def on_message(self, message):
        self.counter["messages_read"] += 1
        if message.author.bot:
            return
        await self.process_commands(message)

    async def close(self):
        await super().close()
        await self.close()

    async def on_shard_ready(self, shard_id):
        if not hasattr(self, 'uptime'):
            self.uptime = datetime.datetime.utcnow()
        print(f"Shard {shard_id} Connected...")
        webhook_url = f"https://discordapp.com/api/webhooks/{config.webhook_id}/{config.webhook_token}"
        payload = {
            "embeds": [
                {
                    "title": "Shard Connect.",
                    "description": f"Shard {shard_id} has connected.",
                    "color": 14593471
                }
            ]
        }
        async with aiohttp.ClientSession() as cs:
            async with cs.post(webhook_url, json=payload) as r:
                res = await r.read()
                print(res)

    async def on_ready(self):
        print("             _         _           _   \n"
              "            | |       | |         | |  \n"
              "  _ __   ___| | _____ | |__   ___ | |_ \n"
              " | '_ \ / _ \ |/ / _ \| '_ \ / _ \| __|\n"
              " | | | |  __/   < (_) | |_) | (_) | |_ \n"
              " |_| |_|\___|_|\_\___/|_.__/ \___/ \__|\n"
              "                                       \n"
              "                                       ")
        print("Ready OwO")
        print(f"Shards: {self.shard_count}")
        print(f"Servers {len(self.guilds)}")
        print(f"Users {len(set(self.get_all_members()))}")
        await self.change_presence(status=discord.Status.idle)

        channel = self.get_channel(441571998943150082)
        while True:
            async with aiohttp.ClientSession() as cs:
                async with cs.get(f'https://nekobot.xyz/api/image?type={random.choice(["neko", "lewdneko"])}') as r:
                    res = await r.json()
                    em = discord.Embed(color=0xDEADBF)
                    em.set_image(url=res['message'])
                    await channel.send(embed=em)
            await asyncio.sleep(900)

    def run(self):
        super().run(config.token)

def run_bot():
    bot = NekoBot()
    bot.run()

if __name__ == '__main__':
    run_bot()
