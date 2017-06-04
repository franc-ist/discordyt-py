# this is a full (minimalist) rewrite of the bot, slimmed down with no impact on users

import aiohttp
import urllib.request
import requests # used for local testing cause macOS is a bum
import sys
import asyncio
import time
import re
import subprocess
import datetime
import time
from decimal import Decimal
import os
import json

import logging # logging
import logging.handlers
import traceback
# apis
import discord # discord api
from discord.ext import commands # commands extension
from discord.ext.commands import when_mentioned_or # allows repsonse when mentioned
from apiclient.discovery import build # youtube api

description = '''Minimalist rewrite of the YouTube bot'''

bot = commands.Bot(command_prefix=when_mentioned_or('ytb '), description=description)
session = aiohttp.ClientSession(loop=bot.loop)

sys.modules['win32file'] = None # Some systems will crash without this because Google's Python is built differently
youtube_key = 'YOUTUBE API KEY'
dbots_key = 'DBOTS KEY'

def set_logger():
    global logger
    logger = logging.getLogger("discord")
    logger.setLevel(logging.WARNING)
    handler = logging.FileHandler(
        filename='discord.log', encoding='utf-8', mode='a')
    handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s Discord: %(funcName)s (Line %(lineno)d): '
        '%(message)s',
        datefmt="[%d/%m/%Y %H:%M]"))
    logger.addHandler(handler)

    logger = logging.getLogger("yt")
    logger.setLevel(logging.INFO)

    yt_format = logging.Formatter(
        '%(asctime)s %(levelname)s YouTube Beta Code: %(funcName)s (Line %(lineno)d): '
        '%(message)s',
        datefmt="[%d/%m/%Y %H:%M]")

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(yt_format)
    stdout_handler.setLevel(logging.INFO)

    fhandler = logging.handlers.RotatingFileHandler(
        filename='ytb.log', encoding='utf-8', mode='a',
        maxBytes=10**7, backupCount=5)
    fhandler.setFormatter(yt_format)

    logger.addHandler(fhandler)
    logger.addHandler(stdout_handler)

@bot.event
async def on_command_error(error, ctx):
    if isinstance(error, commands.MissingRequiredArgument):
        await send_cmd_help(ctx)
    elif isinstance(error, commands.BadArgument):
        await send_cmd_help(ctx)
    elif isinstance(error, commands.CommandOnCooldown):
        await ctx.bot.send_message(ctx.message.channel, "Woah there, {}. That command is on cooldown!".format(ctx.message.author.mention))
    elif isinstance(error, commands.CommandInvokeError):
        logger.exception("Exception in command '{}'".format(
            ctx.command.qualified_name), exc_info=error.original)
        oneliner = "Error in command '{}' - {}: {}".format(
            ctx.command.qualified_name, type(error.original).__name__,
            str(error.original))
        await ctx.bot.send_message(ctx.message.channel, oneliner)
    elif isinstance(error, commands.CommandNotFound):
        pass
    elif isinstance(error, commands.CheckFailure):
        pass
    else:
        logger.exception(type(error).__name__, exc_info=error)

@bot.event
async def on_ready():
    bot.uptime = datetime.datetime.utcnow()
    global logger
    users = len(set(bot.get_all_members()))
    servers = len(bot.servers)
    channels = len([c for c in bot.get_all_channels()])
    await bot.change_presence(game=discord.Game(name='yt beta'))
    await bot.update()
    logger.info('Logged in as {}'.format(str(bot.user)))
    logger.info("Connected to:")
    logger.info("{} servers".format(servers))
    logger.info("{} channels".format(channels))
    logger.info("{} users\n".format(users))

class YouTube:
    """Youtube Commands"""

    @bot.command(pass_context=True, aliases=["s"])
    async def search(ctx):
        """Searches YouTube for a video. 

        Returns the first result."""
        try:
            await bot.send_typing(ctx.message.channel)
            if len(ctx.message.content.split(' ', 2)) == 2:
                await bot.say("Arguments needed!\n\nExample: `yt search Darude Sandstorm`")
            else:
                youtube = build("youtube", "v3", developerKey=youtube_key)
                search_response = youtube.search().list(q=ctx.message.content.split(' ', 2)[2],part="id,snippet",maxResults=1,type="video").execute()
                if len(search_response.get('items')) == 0:
                    await bot.say("No videos found.")
                else:
                    vidid = search_response.get('items')[0]['id']['videoId']
                    vidurl = "https://www.youtube.com/watch?v=" + vidid
                    yt_url = "http://www.youtube.com/oembed?url={0}&format=json".format(vidurl)
                    metadata = await get_json(yt_url)
                    data = discord.Embed(title="**__Search Result__**", colour=discord.Colour(value=11735575))
                    data.add_field(name="Video Title", value=metadata['title'], inline=False)
                    data.add_field(name="Video Uploader", value=metadata['author_name'], inline=False)
                    data.add_field(name="Video Link", value=vidurl, inline=False)
                    data.set_image(url="https://i.ytimg.com/vi/{}/hqdefault.jpg".format(vidid))
                    data.set_footer(text="Made with \U00002665 by Francis#6565. Support server: https://discord.gg/yp8WpMh")
                    try:
                        await bot.say(embed=data)
                    except discord.HTTPException:
                        logger.exception("Missing embed links perms")
                        await bot.say("Looks like the bot doesn't have embed links perms... It kinda needs these, so I'd suggest adding them!")
        except Exception as e:
            logger.exception(e)
            data = discord.Embed(title="__***Error in video search!***__", description="No data for video ID!", colour=discord.Colour(value=11735575))
            data.add_field(name="Whoops!", value="Looks like the API returned a video, but there is no associated data with it!\nThis could be due to the video being unavailable anymore, or it is country blocked!", inline=False)
            data.add_field(name="What can I do now?", value="Not much really. *__Please don't re-search the video__*, as this adds unnecessary strain on the bot, and you'll get the same result.", inline=False)
            data.set_footer(text="Made with \U00002665 by Francis#6565")
            try:
                await bot.say(embed=data)
            except discord.HTTPException:
                logger.exception("Missing embed links perms")
                await bot.say("Looks like the bot doesn't have embed links perms... It kinda needs these, so I'd suggest adding them!")

    @bot.command(pass_context=True, aliases=["c"])
    async def channel(ctx):
        """Searches YouTube for a channel. 

        Returns the first result."""
        try:
            await bot.send_typing(ctx.message.channel)
            if len(ctx.message.content.split(' ', 2)) == 2:
                await bot.say("Arguments needed!\n\nExample: `yt channel TrapNation`")
            else:
                youtube = build("youtube", "v3", developerKey=youtube_key)
                search_response = youtube.search().list(q=ctx.message.content.split(' ', 2)[2],part="id,snippet",maxResults=1,type="channel").execute()
                if len(search_response.get('items')) == 0:
                    await bot.say("No channels found.")
                else:
                    chanid = search_response.get('items')[0]['id']['channelId']
                    data = youtube.channels().list(part='statistics,snippet', id=chanid).execute()
                    subs = str(data['items'][0]['statistics']['subscriberCount'])
                    subsf = thous(subs)
                    name = str(data['items'][0]['snippet']['title'])
                    img = str(data['items'][0]['snippet']['thumbnails']['medium']['url'])
                    chanurl = "https://www.youtube.com/channel/" + chanid
                    data = discord.Embed(title="**__Search Result__**", colour=discord.Colour(value=11735575))
                    data.add_field(name="Channel Name", value=name, inline=False)
                    data.add_field(name="Subscribers", value=subsf, inline=False)
                    data.add_field(name="Channel Link", value=chanurl, inline=False)
                    data.set_image(url=img)
                    data.set_footer(text="Made with \U00002665 by Francis#6565. Support server: https://discord.gg/yp8WpMh")
                    try:
                        await bot.say(embed=data)
                    except discord.HTTPException:
                        logger.exception("Missing embed links perms")
                        await bot.say("Looks like the bot doesn't have embed links perms... It kinda needs these, so I'd suggest adding them!")
        except Exception as e:
            logger.exception(e)
            data = discord.Embed(title="__***Error in channel search!***__", description="No data for channel ID!", colour=discord.Colour(value=11735575))
            data.add_field(name="Whoops!", value="Looks like the API returned a channel, but there is no associated data with it!\nThis could be due to the video being unavailable anymore, or it is country blocked!", inline=False)
            data.add_field(name="What can I do now?", value="Not much really. *__Please don't re-search the channel__*, as this adds unnecessary strain on the bot, and you'll get the same result.", inline=False)
            data.set_footer(text="Made with \U00002665 by Francis#6565")
            try:
                await bot.say(embed=data)
            except discord.HTTPException:
                logger.exception("Missing embed links perms")
                await bot.say("Looks like the bot doesn't have embed links perms... It kinda needs these, so I'd suggest adding them!")

    @bot.command(pass_context=True, aliases=['l'])
    async def lookup(ctx):
        """Reverse lookup for youtube videos. Returns statistics and stuff"""
        try:
            await bot.send_typing(ctx.message.channel)
            if len(ctx.message.content.split(' ', 2)) == 2:
                await bot.say("Arguments needed!\n\nExample: `yt lookup https://www.youtube.com/watch?v=dQw4w9WgXcQ`")
            else:
                url = re.compile(r'http(?:s?):\/\/(?:www\.)?youtu(?:be\.com\/watch\?v=|\.be\/)([\w\-\_]*)(&(amp;)?‌​[\w\?‌​=]*)?')
                shorturl = re.compile(r'http(?:s?):\/\/?youtu(?:\.be\/)([\w\-\_]*)(&(amp;)?‌​[\w\?‌​=]*)?')
                q=ctx.message.content.split(' ', 2)[2]
                match = re.search(url, q)
                if match:
                    match2 = re.search(shorturl, q)
                    if match2:
                        a = match2.group(1)
                        q = 'https://www.youtube.com/watch?v={}'.format(a)
                    yt_url = "http://www.youtube.com/oembed?url={0}&format=json".format(q)
                    metadata = await get_json(yt_url)
                    youtube = build("youtube", "v3", developerKey=youtube_key)
                    search_response = youtube.search().list(q=ctx.message.content.split(' ', 2)[2],part="id,snippet",maxResults=1,type="video").execute()
                    if len(search_response.get('items')) == 0:
                        await bot.say("No videos found.")
                    else:
                        vidid = search_response.get('items')[0]['id']['videoId']
                        data = discord.Embed(title="**__Reverse Lookup__**", colour=discord.Colour(value=11735575))
                        data.add_field(name="Video Title", value=metadata['title'], inline=False)
                        data.add_field(name="Video Uploader", value=metadata['author_name'], inline=False)
                        data.add_field(name="Video Link", value=q, inline=False)
                        data.set_image(url="https://i.ytimg.com/vi/{}/hqdefault.jpg".format(vidid))
                        data.set_footer(text="Made with \U00002665 by Francis#6565. Support server: https://discord.gg/yp8WpMh")
                    try:
                        await bot.say(embed=data)
                    except discord.HTTPException:
                        logger.exception("Missing embed links perms")
                        await bot.say("Looks like the bot doesn't have embed links perms... It kinda needs these, so I'd suggest adding them!")
        except Exception as e:
            logger.exception(e)
            data = discord.Embed(title="__***Error in reverse lookup!***__", description="No data for video ID!", colour=discord.Colour(value=11735575))
            data.add_field(name="Whoops!", value="Looks like the API returned info for the video, but there is no associated data with it!\nThis could be due to the video being unavailable anymore, or it is country blocked!", inline=False)
            data.add_field(name="What can I do now?", value="Not much really. *__Please don't re-search the video__*, as this adds unnecessary strain on the bot, and you'll get the same result.", inline=False)
            data.set_footer(text="Made with \U00002665 by Francis#6565")
            try:
                await bot.say(embed=data)
            except discord.HTTPException:
                logger.exception("Missing embed links perms")
                await bot.say("Looks like the bot doesn't have embed links perms... It kinda needs these, so I'd suggest adding them!")


async def get_json(yt_url):
    async with session.get(yt_url) as r:
        result = await r.json()
    return result

def thous(subs):
    return re.sub(r'(\d{3})(?=\d)', r'\1 ', str(subs)[::-1])[::-1]

class General:
    """General commands, mainly for debugging"""

    @bot.command(pass_context=True, hidden=True)
    async def ping(ctx):
        user_dt = time.mktime(ctx.message.timestamp.timetuple()) + ctx.message.timestamp.microsecond / 1E6
        msg = await bot.say('Pong!')
        bot_dt = time.mktime(msg.timestamp.timetuple()) + msg.timestamp.microsecond / 1E6
        bot_dt = format(bot_dt, ".15g")
        user_dt = format(user_dt, ".15g")
        ping = int(round((Decimal(bot_dt) - Decimal(user_dt)) * 1000))
        data = discord.Embed(title="__Pong!__", colour=discord.Colour(value=11735575))
        data.add_field(name="Response Time", value=str(ping) + " ms", inline=False)
        data.add_field(name="Looking sluggish?", value="Let us know! Join the support server! https://discord.gg/yp8WpMh")
        data.set_footer(text="Made with \U00002665 by Francis#6565.")
        await bot.delete_message(msg)
        try:
            await bot.say(embed=data)
        except discord.HTTPException:
            logger.exception("Missing embed links perms")
            await bot.say("Looks like the bot doesn't have embed links perms... It kinda needs these, so I'd suggest adding them!")

    @bot.command(aliases=['v'])
    async def version():
        """Shows the changelog of the bot"""
        latest_change = "- Started rewrite of bot"
        latest_change += "\n- Started playing with embeds"
        latest_change += "\n- Renamed `yt stats` to `yt lookup`"
        prev_change = "N/A"
        version = "2.0-beta"
        data = discord.Embed(title="__**Changelog**__", colour=discord.Colour(value=11735575))
        data.add_field(name="Version", value=version, inline=False)
        data.add_field(name="Latest Changes", value=latest_change, inline=False)
        data.add_field(name="Previous Changes", value=prev_change, inline=False)
        data.add_field(name="More Info", value="Visit the help server for more info about the bot! https://discord.gg/yp8WpMh")
        data.set_footer(text="Made with \U00002665 by Francis#6565")
        try:
            await bot.say(embed=data)
        except discord.HTTPException:
            logger.exception("Missing embed links perms")
            await bot.say("Looks like the bot doesn't have embed links perms... It kinda needs these, so I'd suggest adding them!")

    @bot.command()
    async def beta():
        """Ooooo new stuff!"""
        data = discord.Embed(title="__**YouTube Beta**__", colour=discord.Colour(value=11735575))
        data.add_field(name="Owo what's this?", value="This is a beta version of the bot. New stuff has been added and should be stable, but may break.")
        data.add_field(name="Oh, cool! What is new?", value="In this version, I've rewritten the entire bot for efficiency, and added rich embeds.")
        data.add_field(name="What if it breaks?", value="I'm always happy to give support, and look for feedback. You can find me on the support server! https://discord.gg/yp8WpMh")
        data.set_footer(text="Made with \U00002665 by Francis#6565.")
        try:
            await bot.say(embed=data)
        except discord.HTTPException:
            logger.exception("Missing embed links perms")
            await bot.say("Looks like the bot doesn't have embed links perms... It kinda needs these, so I'd suggest adding them!")

    @bot.command(aliases=['i'])
    async def info():
        """Information about the bot"""
        shards = 10
        shard_id = 1
        servers = len(list(bot.servers))


        url = 'https://www.carbonitex.net/discord/api/bot/info?id=205224819883638785'

        r = urllib.request.urlopen(url).read()
        print(r)



        total_servers = r[6]

        users = str(len([m for m in set(bot.get_all_members())]))
        channels = str(len([m for m in set(bot.get_all_channels())]))

        since = bot.uptime.strftime("%H:%M:%S %d/%m/%Y")
        passed = get_bot_uptime()

        uptime = '{} (Since {})'.format(passed, since)

        data = discord.Embed(title="__**Information**__", colour=discord.Colour(value=11735575))
        data.add_field(name="Version", value="2.0-beta", inline=False)
        data.add_field(name="Shard ID", value=shard_id)
        data.add_field(name="Total Shards", value=shards)
        data.add_field(name="Servers (on this shard)", value=servers)
        data.add_field(name="Servers (total)", value=total_servers)
        data.add_field(name="Users (on this shard)", value=users)
        data.add_field(name="Channels (on this shard)", value=channels)
        data.add_field(name="Uptime", value=uptime, inline=False)
        data.set_image(url="https://franc.ist/images/YouTubeFM.png")
        data.set_footer(text="Made with \U00002665 by Francis#6565. Support server: https://discord.gg/yp8WpMh")

        try:
            await bot.say(embed=data)
        except discord.HTTPException:
            logger.exception("Missing embed links perms")
            await bot.say("Looks like the bot doesn't have embed links perms... It kinda needs these, so I'd suggest adding them!")


def get_bot_uptime(brief=False):  # KINDA BORKED
    # Courtesy of Danny
    now = datetime.datetime.utcnow()
    delta = now - bot.uptime
    hours, remainder = divmod(int(delta.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)
    days, hours = divmod(hours, 24)

# general things


#stats updating
@bot.event
async def update():

    # payload = json.dumps({
    #     'shard_id': 9,
    #     'shard_count': 10,
    #     'server_count': len(bot.servers)
    # })

    # headers = {
    #     'authorization': dbots_key,
    #     'content-type': 'application/json'
    # }

    # DISCORD_BOTS_API = 'https://bots.discord.pw/api'

    # url = '{0}/bots/205224819883638785/stats'.format(DISCORD_BOTS_API)
    # async with session.post(url, data=payload, headers=headers) as resp:
    #     logger.info('UPDATED SERVER COUNT\nDBots statistics returned {0.status} for {1}\n'.format(resp, payload))

    payload = {
         'shard_id': 1,
         'shard_count': 1,
         'servercount': len(bot.servers)
    }

    headers = {
        'user-agent': 'YouTube/2.0',
        'content-type': 'application/json'
    }


    url = 'https://www.carbonitex.net/discord/data/botdata.php?key=CARBONKEY'
    async with session.post(url, data=payload, headers=headers) as resp:
        logger.info('UPDATED SERVER COUNT\nCarbon statistics returned {0.status} for {1}\n'.format(resp, payload))


@bot.event
async def on_server_join(server):
    await bot.update()

@bot.event
async def on_server_leave(server):
    await bot.update()

        

# login stuff
def main():
    set_logger()
    try:
        yield from bot.login('DISCORD TOKEN GOES HERE') 
        # login here
        yield from bot.connect()
    except TypeError as e:
        logger.warning(e)
        msg = ("\nYou are using an outdated discord.py.\n"
               "update your discord.py with by running this in your cmd "
               "prompt/terminal.\npip3 install --upgrade git+https://"
               "github.com/Rapptz/discord.py@async")
        sys.exit(msg)


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())
    except discord.LoginFailure:
        logger.error(traceback.format_exc())
    except:
        logger.error(traceback.format_exc())
        loop.run_until_complete(bot.logout())
    finally:
        loop.close()
