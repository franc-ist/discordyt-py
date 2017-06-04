import discord  # discord api
from discord.ext import commands  # commands extension

import aiohttp
import time
from datetime import datetime
import datetime
from modules.utils import checks
import inspect
import logging
from decimal import Decimal

from datadog import initialize

options = {
    'api_key': 'datadog api key',
    'app_key': 'datadog app key'
}

initialize(**options)
import datadog
from datadog import statsd


class General:
    """General commands, mainly for debugging"""

    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession(loop=self.bot.loop)

    @commands.command(hidden=True)
    async def ping(self, ctx):
        user_dt = time.mktime(ctx.message.created_at.timetuple(
        )) + ctx.message.created_at.microsecond / 1E6
        msg = await ctx.send('Pong!')
        bot_dt = time.mktime(msg.created_at.timetuple()) + \
            msg.created_at.microsecond / 1E6
        bot_dt = format(bot_dt, ".15g")
        user_dt = format(user_dt, ".15g")
        ping = int(round((Decimal(bot_dt) - Decimal(user_dt)) * 1000))
        data = discord.Embed(
            title="__Pong!__", colour=discord.Colour(value=11735575))
        data.add_field(name="Response Time", value=str(
            ping) + " ms", inline=False)
        data.add_field(name="Looking sluggish?",
                       value="Let us know! Join the support server! https://discord.gg/yp8WpMh")
        data.set_footer(text="Made with \U00002665 by Francis#6565.")
        try:
            await msg.edit(content=None, embed=data)
            statsd.increment('bot.commands.run', 1)
        except discord.HTTPException:
            statsd.increment('bot.commands.errored', 1)
            logger.exception("Missing embed links perms")
            await ctx.send("Looks like the bot doesn't have embed links perms... It kinda needs these, so I'd suggest adding them!")

    @commands.command(aliases=['v'])
    async def version(self, ctx):
        """Shows the changelog of the bot"""
        latest_change = "New Commands:"
        latest_change += "\n- `yt latest`"
        # latest_change += "\n- `yt"
        latest_change += "\n- Backend changes for connections to 3rd party services (e.g. discordbots.org)"
        latest_change += "\n- Updated to work with [discord.py 1.0.0](http://discordpy.readthedocs.io/en/rewrite/)"
        prev_change = "Initial rewrite of bot"
        latest_change += "\nRenamed `yt stats` to `yt lookup`"
        version = "2.5-beta"
        data = discord.Embed(title="__**Changelog**__",
                             colour=discord.Colour(value=11735575))
        data.add_field(name="Version", value=version, inline=False)
        data.add_field(name="Latest Changes",
                       value=latest_change, inline=False)
        data.add_field(name="Previous Changes",
                       value=prev_change, inline=False)
        data.add_field(
            name="More Info", value="Visit the [support server](https://discord.gg/yp8WpMh) for more info about the bot!")
        data.set_footer(text="Made with \U00002665 by Francis#6565")
        try:
            await ctx.send(embed=data)
            statsd.increment('bot.commands.run', 1)
        except discord.HTTPException:
            statsd.increment('bot.commands.errored', 1)
            logger.exception("Missing embed links perms")
            await ctx.send("Looks like the bot doesn't have embed links perms... It kinda needs these, so I'd suggest adding them!")

    @commands.command()
    async def beta(self, ctx):
        """Ooooo new stuff!"""
        data = discord.Embed(title="__**YouTube Beta**__",
                             colour=discord.Colour(value=11735575))
        data.add_field(name="Owo what's this?",
                       value="This is a beta version of the bot. New stuff has been added and should be stable, but may break.")
        data.add_field(name="Oh, cool! What is new?",
                       value="In this version, I've added some new commands (yt beta) and upgraded to [discord.py 1.0.0](http://discordpy.readthedocs.io/en/rewrite/)")
        data.add_field(name="What if it breaks?",
                       value="I'm always happy to give support, and look for feedback. You can find me on the [support server](https://discord.gg/yp8WpMh)!")
        data.set_footer(text="Made with \U00002665 by Francis#6565.")
        try:
            await ctx.send(embed=data)
            statsd.increment('bot.commands.run')
        except discord.HTTPException:
            logger.exception("Missing embed links perms")
            statsd.increment('bot.commands.errored', 1)
            await ctx.send("Looks like the bot doesn't have embed links perms... It kinda needs these, so I'd suggest adding them!")

    @commands.command()
    async def join(self, ctx):
        """Get a link for the bot to join your server!"""
        try:
            data = await self.bot.application_info()
        except AttributeError:
            return "Your discord.py is outdated. Couldn't retrieve invite link."
        url = discord.utils.oauth_url(
            data.id, permissions=discord.Permissions(permissions=84992))
        await ctx.send("To invite the bot, use this link: <{}>".format(url))
        statsd.increment('bot.commands.run', 1)

    @commands.command(aliases=['i'])
    async def info(self, ctx):
        """Information about the bot"""
        msg = await ctx.send('Getting statistics...')
        shards = self.bot.shard_count
        shard_id = ctx.message.guild.shard_id
        guilds = len(list(self.bot.guilds))
        users = str(len([m for m in set(self.bot.get_all_members())]))

        channels = str(len([m for m in set(self.bot.get_all_channels())]))
        # await msg.edit("Getting uptime...")
        up = abs(self.bot.uptime - int(time.perf_counter()))
        up = str(datetime.timedelta(seconds=up))

        data = discord.Embed(title="__**Information**__",
                             colour=discord.Colour(value=11735575))
        data.add_field(name="Version", value="2.5-beta", inline=False)
        data.add_field(name="Shard ID", value=ctx.message.guild.shard_id)
        data.add_field(name="Total Shards", value=shards)
        data.add_field(name="Total Servers", value=guilds)
        # data.add_field(name="Servers (total)", value=total_guilds)
        data.add_field(name="Users", value=users)
        data.add_field(name="Channels", value=channels)
        data.add_field(name="Uptime", value="{}".format(up))
        data.add_field(name="Support Development",
                       value="Donate on [Patreon](https://www.patreon.com/franc_ist) or [PayPal](https://paypal.me/MLAutomod/5)")
        data.set_footer(
            text="Made with \U00002665 by Francis#6565. Support server: https://discord.gg/yp8WpMh")
        try:
            await msg.edit(content=None, embed=data)
            statsd.increment('bot.commands.run', 1)
        except discord.HTTPException:
            logger.exception("Missing embed links perms")
            statsd.increment('bot.commands.errored', 1)
            await ctx.send("Looks like the bot doesn't have embed links perms... It kinda needs these, so I'd suggest adding them!")

    @commands.command(aliases=['up'])
    async def uptime(self, ctx):
        """Shows the bot's uptime"""
        up = abs(self.bot.uptime - int(time.perf_counter()))
        up = str(datetime.timedelta(seconds=up))
        await ctx.send("`Uptime: {}`".format(up))
        statsd.increment('bot.commands.run', 1)


def setup(bot):
    global logger
    logger = logging.getLogger('yt')
    bot.add_cog(General(bot))
