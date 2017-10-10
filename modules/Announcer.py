# this is currently a mess as i moved from dataIO to rethink

import discord
from discord.ext import commands
from apiclient.discovery import build  # youtube api

import asyncio
import sys
import logging
import aiohttp
import re
import time
import os

import rethinkdb as r
from rethinkdb.errors import RqlRuntimeError, RqlDriverError

RDB_HOST =  os.environ.get('RDB_HOST') or 'localhost'
RDB_PORT = os.environ.get('RDB_PORT') or 28015
YT_DB = 'yt'



from modules.utils import checks
from __main__ import send_cmd_help

# okay here goes... autoannounce new videos
# dataIO format : dataIO.function(path, data)

# Some systems will crash without this because Google's Python is built
# differently
sys.modules['win32file'] = None
youtube_key = '***REMOVED***'

def dbSetup():
    connection = r.connect(host=RDB_HOST, port=RDB_PORT)
    try:
        r.db_create(YT_DB).run(connection)
        r.db(YT_DB).table_create('yt').run(connection)
        logger.info('Database setup completed. Now run the app without --setup.')
    except RqlRuntimeError:
        logger.exception('App database already exists. Run the app without --setup.')
    finally:
        connection.close()
    r.table('yt').index_create('guildId').run()
    r.table('yt').index_wait('guildId').run()

from datadog import initialize

options = {
    'api_key': '***REMOVED***',
    'app_key': '***REMOVED***'
}

initialize(**options)
import datadog
from datadog import statsd

class Announcer:
    """Auto announcer for YouTube Videos"""

    def __init__(self, bot):
        self.bot = bot
        self.default_settings = {
            'mentionHere': False,
            'mentionEveryone': False,
            'message': 'New video! ',
            'yt_channel': None,
            'latest_video': None,
            'channel': None
        }
        self.refresh_interval = 60

    @commands.group(no_pm=True)
    async def announce(self, ctx):
        """Manages video announcing"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help()

    @announce.command(name="list", no_pm=True)
    async def _list_channels(self, ctx):
        """Lists YouTube channels with announcements enabled"""
        guild = ctx.message.guild
        if guild.id in self.ids:
            try:
                data = discord.Embed(
                    title="**__Announcement Channels__**\n", colour=discord.Colour(value=11735575))
                k = self.ids[guild.id]['yt_channel']
                data.add_field(
                    name="YouTube Channel", value=k)
                data.add_field(
                    name="Discord Channel", value=self.ids[guild.id]['channel'])
                data.set_footer(
                    text="Made with \U00002665 by Francis#6565. Support server: https://discord.gg/yp8WpMh")
                await ctx.send(embed=data)
            except IndexError as e:
                logger.exception(
                    "An error occured while pulling data from list... {}".format(e))

    @announce.command(name="add", no_pm=True)
    async def _add_channel(self, ctx, *, ytchannel):
        """Adds a new channel for video announcements. Run this command in the Discord channel you want announcements for."""
        guild = ctx.message.guild
        channel = ctx.message.channel
        if r.table('yt').get(guild.id, index="guildId").run():
            continue
        else:
            await ctx.send('Looks like this channel isn\'t in the database!\nAdding record now with default settings! You can change this with `yt settings`.')
            logger.info("Creating new guild data for announce. ID (Server, Channel): {} , {}".format(guild.id, channel.id))
            r.table('yt').insert([
                { "guildId" : guild.id, 
                "channelId" : channel.id,
                'mentionHere': False,
                'mentionEveryone': False,
                'message': 'New video! ',
                'yt_channel': None,
                'latest_video': None}]).run()

            logger.info('Created successfully')
        if len(ctx.message.content.split(' ', 3)) == 3:
            await ctx.send("Arguments needed!\n\nExample: `yt announce add DramaAlert`")
        else:
            youtube = build("youtube", "v3", developerKey=youtube_key)
            search_response = youtube.search().list(q=ctx.message.content.split(
                ' ', 3)[3], part="id,snippet", maxResults=1, type="channel").execute()
            ytchannelid = search_response.get('items')[0]['id']['channelId']
            await ctx.send("Adding channel {} to announcements. Continue? (y/n)".format(ytchannelid))
            # wait for input
            logger.info(self.ids[guild.id])
            logger.info(self.ids[guild.id]['yt_channel'])
            if self.ids[guild.id]['yt_channel'] is not None:
                yt_channel = [self.ids[guild.id]['yt_channel'], ytchannelid]
            else:
                yt_channel = ytchannelid
            self.ids[guild.id]['yt_channel'] = yt_channel
            self.ids[guild.id]['channel'] = channel.id
            dataIO.save_json(self.ids_path, self.ids)
            await ctx.send('Enabled announcements for channel id {} ({}) in this channel!'.format(ytchannelid, search_response['items'][0]['snippet']['title']))

    @announce.command(name="remove", no_pm=True)
    async def _remove_channel(self, ctx, ytchannel):
        """Removes video announcements for a channel. Run this command in the Discord channel you want to disable announcements in."""
        guild = ctx.message.guild
        channel = ctx.message.channel
        if guild.id not in self.ids:
            await ctx.send('Error: No announcements configured for this server.')
        if len(ctx.message.content.split(' ', 3)) == 3:
            await ctx.send("Arguments needed!\n\nExample: `yt announce add DramaAlert`")
        else:
            youtube = build("youtube", "v3", developerKey=youtube_key)
            search_response = youtube.search().list(q=ctx.message.content.split(
                ' ', 3)[3], part="id,snippet", maxResults=1, type="channel").execute()
            ytchannelid = search_response.get('items')[0]['id']['channelId']
        if self.ids[guild.id]['yt_channel'] is ytchannelid:
            self.ids[guild.id]['yt_channel'] = None
        else:
            yt_channel = self.ids[guild.id]['yt_channel']
            yt_channel.remove(ytchannelid)
            self.ids[guild.id]['yt_channel'] = yt_channel
            dataIO.save_json(self.ids_path, self.ids)

    @commands.group(no_pm=True)
    @checks.serverowner_or_permissions()
    async def settings(self, ctx):
        """Manages settings for video announcing"""
        guild = ctx.message.guild
        channel = ctx.message.channel
        settings = self.ids[guild.id]
        if ctx.invoked_subcommand is None:
            msg = "```"
            for k, v in settings.items():
                msg += "{}: {}\n".format(k, v)
            msg += "```"
            await send_cmd_help(ctx)
            await ctx.send(msg)

    @settings.command(name="everyone", no_pm=True)
    async def _mention_all(self, ctx, *mention: str):
        """Mentions everyone when a video is uploaded if enabled.

        Usage: `yt settings everyone [True/False]`"""
        guild = ctx.message.guild
        channel = ctx.message.channel
        if mention == 'True':
            await ctx.send('Enabling @\U0000200Beveryone mentions.')
            self.ids[guild.id][mentionEveryone] = True
        elif mention == 'False':
            await ctx.send('Disabling @\U0000200Beveryone mentions.')
            self.ids[guild.id][mentionEveryone] = False
        else:
            await ctx.send('Error: Incorrect Value. Please specify True or False (case sensitive).')
        dataIO.save_json(self.ids_path, self.ids)

    @settings.command(name="here", no_pm=True)
    async def _mention_here(self, ctx, *mention: str):
        """Mentions everyone when a video is uploaded if enabled.

        Usage: `yt settings here [True/False]`"""
        guild = ctx.message.guild
        channel = ctx.message.channel
        if mention == 'True':
            await ctx.send('Enabling @\U0000200Bhere mentions.')
            self.ids[guild.id][mentionHere] = True
        elif mention == 'False':
            await ctx.send('Disabling @\U0000200Bhere mentions.')
            self.ids[guild.id][mentionHere] = False
        else:
            await ctx.send('Error: Incorrect Value. Please specify True or False (case sensitive).')
        dataIO.save_json(self.ids_path, self.ids)

    @settings.command(name="message", no_pm=True)
    async def _message(self, ctx, *msg: str):
        """Sets the message to display on a new video.

        Leave blank to reset"""
        guild = ctx.message.guild
        channel = ctx.message.channel
        if msg == None:
            msg = "New Video! "
        self.ids[guild.id]['message'] = msg
        dataIO.save_json(self.ids_path, self.ids)
        await ctx.send("Set the message to `{}`".format(msg))


def check_folders():
    if not os.path.exists("data/announce"):
        print("Creating data/announce folder...")
        os.makedirs("data/announce")


def check_files():

    f = "data/announce/ids.json"
    if not dataIO.is_valid_json(f):
        print("Creating default announce ids.json...")
        dataIO.save_json(f, {})


def setup(bot):
    global logger
    logger = logging.getLogger('yt')
    check_folders()
    check_files()
    bot.add_cog(Announcer(bot))
