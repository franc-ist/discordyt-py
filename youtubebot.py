# this is a full (minimalist) rewrite of the bot, "slimmed down" with no
# impact on users

import aiohttp
import urllib.request
import requests  # used for local testing cause macOS is a bum
import sys
import asyncio
import time
import re
import subprocess
import datetime
import time
import os
import json


from modules.utils.dataIO import dataIO

import logging  # logging
import logging.handlers
import traceback
# apis
import discord  # discord api
from discord.ext import commands  # commands extension
# allows repsonse when mentioned
from discord.ext.commands import when_mentioned_or
from apiclient.discovery import build  # youtube api
from datadog import initialize

options = {
    'api_key': '',
    'app_key': ''
}

initialize(**options)
import datadog
from datadog import statsd


description = '''Minimalist rewrite of the YouTube bot'''

bot = commands.AutoShardedBot(command_prefix=when_mentioned_or(
    'yt '), description=description, shard_count=10)
session = aiohttp.ClientSession(loop=bot.loop)


def set_logger():
    global logger
    logger = logging.getLogger("discord")
    logger.setLevel(logging.INFO)
    handler = logging.FileHandler(
        filename='discord.log', encoding='utf-8', mode='a')
    handler.setFormatter(logging.Formatter(
        '\n%(asctime)s %(levelname)s Discord: %(funcName)s (Line %(lineno)d): '
        '%(message)s',
        datefmt="[%d/%m/%Y %H:%M]"))
    logger.addHandler(handler)

    logger = logging.getLogger("yt")
    logger.setLevel(logging.INFO)

    yt_format = logging.Formatter(
        '%(asctime)s %(levelname)s YouTube Code: %(funcName)s (Line %(lineno)d): '
        '%(message)s',
        datefmt="[%d/%m/%Y %H:%M]")

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(yt_format)
    stdout_handler.setLevel(logging.INFO)

    fhandler = logging.handlers.RotatingFileHandler(
        filename='yt.log', encoding='utf-8', mode='a',
        maxBytes=10**7, backupCount=5)
    fhandler.setFormatter(yt_format)

    logger.addHandler(fhandler)
    logger.addHandler(stdout_handler)


@bot.event
async def on_command_error(ctx, error):
    statsd.increment('bot.commands.errored', 1)
    if isinstance(error, commands.MissingRequiredArgument):
        await send_cmd_help(ctx)
    elif isinstance(error, commands.BadArgument):
        await send_cmd_help(ctx)
    elif isinstance(error, commands.CommandOnCooldown):
        await ctx.send("Woah there, {}. That command is on cooldown!".format(ctx.message.author.mention))
    elif isinstance(error, commands.CommandInvokeError):
        logger.exception("Exception in command '{}'".format(
            ctx.command.qualified_name), exc_info=error.original)
        oneliner = "Error in command '{}' - {}: {}".format(
            ctx.command.qualified_name, type(error.original).__name__,
            str(error.original))
        await ctx.send(oneliner)
    elif isinstance(error, commands.CommandNotFound):
        pass
    elif isinstance(error, commands.CheckFailure):
        pass
    else:
        logger.exception(type(error).__name__, exc_info=error)


@bot.event
async def send_cmd_help(ctx):
    if ctx.invoked_subcommand:
        pages = bot.formatter.format_help_for(ctx, ctx.invoked_subcommand)
        for page in pages:
            await bot.send_message(ctx.message.channel, page)
    else:
        pages = bot.formatter.format_help_for(ctx, ctx.command)
        for page in pages:
            await bot.send_message(ctx.message.channel, page)


class Formatter(commands.HelpFormatter):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _add_subcommands_to_page(self, max_width, commands):
        for name, command in sorted(commands, key=lambda t: t[0]):
            if name in command.aliases:
                # skip aliases
                continue

            entry = '  {0:<{width}} {1}'.format(name, command.short_doc,
                                                width=max_width)
            shortened = self.shorten(entry)
            self._paginator.add_line(shortened)


@bot.event
async def on_ready():
    global logger
    logger.info('Discord ready. Loading extensions...')
    extensions = ['modules.Owner', 'modules.General', 'modules.YouTube']
    for extension in extensions:
        try:
            bot.load_extension(extension)
            logger.info("loaded {}".format(extension))
        except Exception as e:
            logger.exception('Failed to load extension {}\n{}: {}'.format(
                extension, type(e).__name__, e))
    if not hasattr(bot, "uptime"):
        bot.uptime = int(time.perf_counter())
    # users = len(set(bot.get_all_members()))
    guilds = len(bot.guilds)
    # channels = len([c for c in bot.get_all_channels()])
    shard_count = bot.shard_count
    # check_folders()
    # check_files()
    await bot.change_presence(game=discord.Game(name='SUPPORT ME: franc.ist/2sqpMkz'))
    await bot.update()
    logger.info('Logged in as {}'.format(str(bot.user)))
    logger.info("Connected to:")
    logger.info("{} servers ({} shards)".format(
        guilds, shard_count))
    # logger.info("{} channels".format(channels))
    # logger.info("{} users\n".format(users))
    statsd.increment('bot.restarts', 1)


# general things


# stats updating
@bot.event
async def update():

    dbots_key = ''
    Oliy_key = ''

    payload = json.dumps({
        # 'shard_id': guild.shard_id,
        # 'shard_count': bot.shard_count,
        'server_count': len(bot.guilds)
    })

    headers = {
        'authorization': dbots_key,
        'content-type': 'application/json'
    }

    headers2 = {
        'authorization': Oliy_key,
        'content-type': 'application/json'
    }

    DISCORD_BOTS_API = 'https://bots.discord.pw/api'
    Oliy_api = 'https://discordbots.org/api'

# discordbots.org 
    url = '{0}/bots/205224819883638785/stats'.format(Oliy_api)
    async with session.post(url, data=payload, headers=headers2) as resp:
        logger.info('SERVER COUNT UPDATED.\ndiscordbots.org statistics returned {0.status} for {1}\n'.format(
            resp, payload))

# bots.discord.pw
    url = '{0}/bots/205224819883638785/stats'.format(DISCORD_BOTS_API)
    async with session.post(url, data=payload, headers=headers) as resp:
        logger.info('SERVER COUNT UPDATED.\nbots.discord.pw statistics returned {0.status} for {1}\n'.format(
            resp, payload))

    url = 'https://discordbots.org/api/bots/205224819883638785/stats'

    statsd.gauge('bot.servers.total', len(bot.guilds))

# carbonitex
    payload = {
        # 'shard_id': guild.shard_id,
        # 'shard_count': bot.shard_count,
        'guild_count': len(bot.guilds)
    }

    headers3 = {
        'user-agent': 'YouTube/2.0',
        'content-type': 'application/json'
    }

    url = 'https://www.carbonitex.net/discord/data/botdata.php?key='
    async with session.post(url, data=payload, headers=headers3) as resp:
        logger.info('UPDATED SERVER COUNT\nCarbon statistics returned {0.status} for {1}\n'.format(
            resp, payload))


@bot.event
async def on_guild_join(guild):
    await bot.update()
    statsd.increment('bot.servers.joined')


@bot.event
async def on_guild_leave(guild):
    await bot.update()
    statsd.increment('bot.servers.left')


# login stuff
def main():
    set_logger()
    try:
        logger.info('Logging in...')
        yield from bot.login('')
        logger.info('Logged in')
        # login here
        logger.info('Connecting to gateway...')
        yield from bot.connect()
        logger.info('Connected to gateway')
        # logger.info('Logging in and connecting...')
        # yield from bot.start('')
        # logger.info('Logged in + connected')
    except TypeError as e:
        logger.warning(e)
        msg = ("\nYou are using an outdated discord.py.\n"
               "update your discord.py with by running this in your cmd "
               "prompt/terminal.\npip3 install --upgrade git+https://github.com/Rapptz/discord.py@rewrite")
        sys.exit(msg)

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())
    except discord.LoginFailure:
        logger.error(traceback.format_exc())
    except KeyboardInterrupt:
        loop.run_until_complete(bot.logout())
    except:
        logger.error(traceback.format_exc())
        loop.run_until_complete(bot.logout())
    finally:
        loop.close()
