from discord.ext import commands
import discord, aiohttp
import random, string, time
import datetime
import asyncio
from .utils.hastebin import post as hastepost
import config
import os, ujson
import logging
from prettytable import PrettyTable

# Languages
languages = ["english", "weeb", "tsundere", "polish", "spanish", "french"]
lang = {}

for l in languages:
    with open("lang/%s.json" % l, encoding="utf-8") as f:
        lang[l] = ujson.load(f)

def getlang(la:str):
    return lang.get(la, None)

log = logging.getLogger()

class Donator:

    def __init__(self, bot):
        self.bot = bot
        self.looder_enabled = False
        self.lood_session = aiohttp.ClientSession(loop=self.bot.loop)

    def id_generator(self, size=7, chars=string.ascii_letters + string.digits):
        return ''.join(random.choice(chars) for _ in range(size))

    async def on_ready(self):
        self.bot.loop.create_task(self.autoloodme())

    async def has_donated(self, userid:int):
        async with self.bot.sql_conn.acquire() as conn:
            async with conn.cursor() as db:
                if not await db.execute("SELECT 1 FROM donator WHERE userid = %s", (userid,)):
                    return False
                else:
                    return True

    async def get_lood_channel(self):
        channels = []
        async with self.bot.sql_conn.acquire() as conn:
            async with conn.cursor() as db:
                await db.execute("SELECT * FROM autolooder")
                all_channels = await db.fetchall()

        for channel in all_channels:
            channels.append(int(channel[0]))

        return channels

    async def get_random_lood(self):
        try:
            base = "https://nekobot.xyz/api/image?type="
            imgtype = random.choice(["lewdneko", "lewdkitsune", "hentai", "neko", "hentai_anal"])
            r = await (await self.lood_session.get(base + imgtype)).json()
            return r["message"]
        except Exception as e:
            log.error("Failed to post, %s" % e)
            return "https://nekobot.xyz/placeholder.png"

    async def autoloodme(self):
        while True:

            for channel in await self.get_lood_channel():
                log.info("Sending loods to %s" % channel)
                try:
                    channel = self.bot.get_channel(channel)
                    if channel.is_nsfw():
                        em = discord.Embed(color=0xDEADBF)
                        em.set_image(url=await self.get_random_lood())
                        await channel.send(embed=em)
                except:
                    pass

            await asyncio.sleep(3600)

    @commands.command(hidden=True)
    @commands.is_owner()
    async def sendkey(self, ctx, user:discord.Member, *, key:str):
        """Send a user their donation key."""
        await ctx.message.add_reaction("👌")
        await user.send(f"Your donation key:\n`{key}`")

    @commands.command(name='trapcard')
    @commands.cooldown(1, 15, commands.BucketType.user)
    async def donator_trapcard(self, ctx, user: discord.Member):
        """Trap a user!"""
        await ctx.trigger_typing()

        lang = await self.bot.redis.get(f"{ctx.message.author.id}-lang")
        if lang:
            lang = lang.decode('utf8')
        else:
            lang = "english"

        author = ctx.message.author

        async with self.bot.sql_conn.acquire() as conn:
            async with conn.cursor() as db:
                await db.execute("SELECT userid FROM donator")
                alltokens = await db.fetchall()
        tokenlist = []
        for x in range(len(alltokens)):
            tokenlist.append(int(alltokens[x][0]))

        if author.id not in tokenlist:
            return await ctx.send(embed=discord.Embed(color=0xff5630, title=getlang(lang)["donator"]["error"]["error"],
                                                      description=getlang(lang)["donator"]["error"]["message"]))

        async with aiohttp.ClientSession() as session:
            url = f"https://nekobot.xyz/api/imagegen" \
                  f"?type=trap" \
                  f"&name={user.name}" \
                  f"&author={author.name}" \
                  f"&image={user.avatar_url_as(format='png')}"
            async with session.get(url) as response:
                t = await response.json()
                await ctx.send(embed=discord.Embed(color=0xDEADBF).set_image(url=t['message']))

    @commands.command(hidden=True)
    @commands.is_owner()
    async def createkey(self, ctx):
        """Create a key"""
        await ctx.trigger_typing()
        x1 = self.id_generator(size=4, chars=string.ascii_uppercase + string.digits)
        x2 = self.id_generator(size=4, chars=string.ascii_uppercase + string.digits)
        x3 = self.id_generator(size=4, chars=string.ascii_uppercase + string.digits)
        token = f"{x1}-{x2}-{x3}"
        await ctx.send(embed=discord.Embed(color=0x8bff87, title="Token Generated", description=f"```css\n"
                                                                                                f"[ {token} ]```"))
        timenow = int(time.time())
        async with self.bot.sql_conn.acquire() as conn:
            async with conn.cursor() as db:
                await db.execute("INSERT INTO donator VALUES (0, %s, %s)", (token, timenow,))

    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def redeem(self, ctx, *, key: str):
        """Redeem your donation key"""
        await ctx.trigger_typing()

        async with self.bot.sql_conn.acquire() as conn:
            async with conn.cursor() as db:
                if not await db.execute("SELECT 1 FROM donator WHERE token = %s", (key,)):
                    return await ctx.send("**Invalid Key**")
                await db.execute("SELECT userid FROM donator")
                alltokens = await db.fetchall()

        tokenlist = []
        for x in range(len(alltokens)):
            tokenlist.append(int(alltokens[x][0]))
        if ctx.message.author.id in tokenlist:
            return await ctx.send("**That key is already active.**")
        async with self.bot.sql_conn.acquire() as conn:
            async with conn.cursor() as db:
                await db.execute("SELECT userid FROM donator WHERE token = %s", (key,))
                user = int((await db.fetchone())[0])
        if user == 0:
            async with self.bot.sql_conn.acquire() as conn:
                async with conn.cursor() as db:
                    await db.execute("UPDATE donator SET userid = %s WHERE token = %s", (ctx.author.id, key,))
            async with aiohttp.ClientSession() as cs:
                webhook = discord.Webhook.from_url(f"https://discordapp.com/api/webhooks/{config.webhook_id}/{config.webhook_token}",
                                                   adapter=discord.AsyncWebhookAdapter(cs))
                await webhook.send(embed=discord.Embed(color=0x8bff87,
                                                   title="Token Accepted",
                                                   description=f"```css\n"
                                                               f"User: {ctx.message.author.name} ({ctx.message.author.id})\n"
                                                               f"Key: [ {key} ]```").set_thumbnail(url=ctx.message.author.avatar_url))
            return await ctx.send("**Token Accepted!**")
        else:
            async with aiohttp.ClientSession() as cs:
                webhook = discord.Webhook.from_url(f"https://discordapp.com/api/webhooks/{config.webhook_id}/{config.webhook_token}",
                                                   adapter=discord.AsyncWebhookAdapter(cs))
                await webhook.send(embed=discord.Embed(color=0xff6f3f,
                                                   title="Token Denied",
                                                   description=f"```css\n"
                                                               f"User: {ctx.message.author.name} ({ctx.message.author.id})\n"
                                                               f"Key: [ {key} ]```").set_thumbnail(url=ctx.message.author.avatar_url))
            return await ctx.send("That key is already in use.")

    @commands.command(hidden=True)
    @commands.is_owner()
    async def keys(self, ctx):
        """View all keys + expiry"""
        await ctx.trigger_typing()
        async with self.bot.sql_conn.acquire() as conn:
            async with conn.cursor() as db:
                await db.execute("SELECT userid, token, usetime FROM donator")
                allkeys = await db.fetchall()
        table = PrettyTable()
        table.field_names = ["User", "Key", "Expiry Date"]
        for key in allkeys:
            expiry = str(datetime.datetime.fromtimestamp(int(key[2])).strftime('%Y-%m-%d'))
            table.add_row([str(key[0]), str(key[1]), expiry])
        x = await hastepost(str(table))
        await ctx.send(x)

    @commands.command(hidden=True)
    @commands.is_owner()
    async def delkey(self, ctx, *, key:str):
        """Delete a key"""
        await ctx.trigger_typing()
        async with self.bot.sql_conn.acquire() as conn:
            async with conn.cursor() as db:
                if not await db.execute("SELECT 1 FROM donator WHERE token = %s", (key,)):
                    return await ctx.send("**Invalid key**")
                else:
                    await db.execute("DELETE FROM donator WHERE token = %s", (key,))
            await ctx.send(f"**Key `{key}` has been deleted.**")
            embed = discord.Embed(color=0xff6f3f, title="Token Deleted",
                                  description=f"```css\n"
                                              f"Key: [ {key} ] \n"
                                              f"```")
            async with aiohttp.ClientSession() as cs:
                webhook = discord.Webhook.from_url(f"https://discordapp.com/api/webhooks/{config.webhook_id}/{config.webhook_token}",
                                                   adapter=discord.AsyncWebhookAdapter(cs))
                await webhook.send(embed=embed)

    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def donate(self, ctx):
        """Donate or Show key time left."""
        await ctx.trigger_typing()
        lang = await self.bot.redis.get(f"{ctx.message.author.id}-lang")
        if lang:
            lang = lang.decode('utf8')
        else:
            lang = "english"
        async with self.bot.sql_conn.acquire() as conn:
            async with conn.cursor() as db:
                await db.execute("SELECT userid FROM donator")
                alltokens = await db.fetchall()
        tokenlist = []
        for x in range(len(alltokens)):
            tokenlist.append(int(alltokens[x][0]))
        if ctx.message.author.id in tokenlist:
            async with self.bot.sql_conn.acquire() as conn:
                async with conn.cursor() as db:
                    await db.execute("SELECT token, usetime FROM donator WHERE userid = %s", (ctx.author.id,))
                    data = await db.fetchone()
                    user_key = data[0]
                    user_time = data[1]

            timeconvert = datetime.datetime.fromtimestamp(int(user_time)).strftime('%Y-%m-%d')
            embed = discord.Embed(color=0xDEADBF, title="Key Info", description=f"Key: `XXXX-XXXX-{user_key[-4:]}`\n"
                                                                                f"Expiry Date: `{timeconvert}`")
            return await ctx.send(embed=embed)
        else:
            return await ctx.send(embed=discord.Embed(color=0xff5630, title=getlang(lang)["donator"]["whats_this"],
                                                  description=getlang(lang)["donator"]["donate"]))

    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def haste(self, ctx, *, text:str):
        """Upload text uwu"""
        author = ctx.message.author
        lang = await self.bot.redis.get(f"{ctx.message.author.id}-lang")
        if lang:
            lang = lang.decode('utf8')
        else:
            lang = "english"

        async with self.bot.sql_conn.acquire() as conn:
            async with conn.cursor() as db:
                await db.execute("SELECT userid FROM donator")
                alltokens = await db.fetchall()
        tokenlist = []
        for x in range(len(alltokens)):
            tokenlist.append(int(alltokens[x][0]))

        if author.id not in tokenlist:
            return await ctx.send(embed=discord.Embed(color=0xff5630, title=getlang(lang)["donator"]["error"]["error"],
                                                      description=getlang(lang)["donator"]["error"]["message"]))

        await ctx.send(await hastepost(text))

    # @commands.command(name='upload')
    # @commands.cooldown(1, 15, commands.BucketType.user)
    # async def donator_upload(self, ctx:commands.Context):
    #     """File Uploader"""
    #     await ctx.trigger_typing()
    #     author = ctx.message.author
    #     lang = await self.bot.redis.get(f"{ctx.message.author.id}-lang")
    #     if lang:
    #         lang = lang.decode('utf8')
    #     else:
    #         lang = "english"
    #
    #     async with self.bot.sql_conn.acquire() as conn:
    #         async with conn.cursor() as db:
    #             await db.execute("SELECT userid FROM donator")
    #             alltokens = await db.fetchall()
    #     tokenlist = []
    #     for x in range(len(alltokens)):
    #         tokenlist.append(int(alltokens[x][0]))
    #
    #     if author.id not in tokenlist:
    #         return await ctx.send(embed=discord.Embed(color=0xff5630, title=getlang(lang)["donator"]["error"]["error"],
    #                                                   description=getlang(lang)["donator"]["error"]["message"]))
    #
    #     await ctx.send("**Send an image/file to upload. Type `cancel` to cancel.**")
    #
    #     def check(m):
    #         return m.author == author and m.channel == ctx.message.channel
    #
    #     msg = await self.bot.wait_for('message', check=check)
    #
    #     if msg.content.lower() in ['cancel', 'Cancel']:
    #         return await ctx.send("**Cancelled.**")
    #
    #     try:
    #         randomnum = self.id_generator()
    #         url = msg.attachments[0].url
    #         attachment = str(url).rpartition('.')[2]
    #         if attachment not in ['png', 'jpg', 'jpeg', 'bmp', 'gif', 'tiff', 'webp']:
    #             return await ctx.send("**File type is forbiddon.**")
    #         await ctx.trigger_typing()
    #         async with aiohttp.ClientSession() as session:
    #             async with session.get(url) as response:
    #                 t = await response.read()
    #
    #         await ctx.send(t["message"])
    #     except Exception as e:
    #         return await ctx.send(f"**Error uploading file**\n\n{e}")

    @commands.command(aliases=["autolood"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.has_permissions(manage_guild=True)
    @commands.guild_only()
    async def autolooder(self, ctx, channel:discord.TextChannel):
        """Enable/Disable the autolooder for your server, mention an already added channel to disable."""

        if not await self.has_donated(ctx.author.id):
            return await ctx.send("You have not donated <a:rainbowNekoDance:462373594555613214>")

        async with self.bot.sql_conn.acquire() as conn:
            async with conn.cursor() as db:
                if await db.execute("SELECT 1 FROM autolooder WHERE channel = %s", (channel.id,)):
                    await db.execute("DELETE FROM autolooder WHERE channel = %s", (channel.id))
                    return await ctx.send("Disabled autolooder from `%s`" % channel.name)

                if channel.is_nsfw():
                    await db.execute("INSERT INTO autolooder VALUES (%s)", (channel.id,))
                    await ctx.send("Enabled autolooder for `%s`" % (channel.name,))
                else:
                    return await ctx.send("That channel is not an NSFW channel.")

def setup(bot):
    bot.add_cog(Donator(bot))