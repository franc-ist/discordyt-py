import discord
from discord.ext import commands
from discord.ext.commands import when_mentioned_or
import aiohttp
import re
import asyncio
from apiclient.discovery import build #youtube api
import sys
import time
import json
from random import choice as randchoice
import git
import logging
import logging.handlers
import traceback
import datetime
import subprocess


description = '''Youtube bot for Discord. Searches YouTube and responds with a link to a video.'''

bot = commands.Bot(command_prefix=when_mentioned_or('ytb '), description=description)
session = aiohttp.ClientSession(loop=bot.loop)

sys.modules['win32file'] = None #Some systems will crash without this because Google's Python is built differently
key = ''
carbon_key = ''
dbots_key = ''

@bot.event
async def on_ready():
    global logger
    if not hasattr(bot, "uptime"):
        bot.uptime = int(time.perf_counter())
    logger.info("-- Logging in... --")
    logger.info("Logged in as {}".format(bot.user.name))
    logger.info("------")
    await bot.change_presence(discord.Game(name='yt search'), discord.Status.dnd) # look at that fancy red-ness
    await bot.update()

@bot.event
async def update():

    payload = json.dumps({
        'server_count': len(bot.servers)
    })

    headers = {
        'authorization': dbots_key,
        'content-type': 'application/json'
    }

    DISCORD_BOTS_API = 'https://bots.discord.pw/api'

    url = '{0}/bots/205224819883638785/stats'.format(DISCORD_BOTS_API)
    async with session.post(url, data=payload, headers=headers) as resp:
        logger.info('SERVER COUNT UPDATED.\nDBots statistics returned {0.status} for {1}\n'.format(resp, payload))

    CARBONITEX_API_BOTDATA = 'https://www.carbonitex.net/discord/data/botdata.php'
    carbon_payload = {
        'key': carbon_key,
        'servercount': len(bot.servers)
    }
    async with self.session.post(CARBONITEX_API_BOTDATA, data=carbon_payload) as resp:
        logger.info('Carbon statistics returned {0.status} for {1}'.format(resp, carbon_payload))

@bot.event
async def on_server_join(server):
    await bot.update()

@bot.event
async def on_server_leave(server):
    await bot.update()

def set_logger():
    global logger
    logger = logging.getLogger("discord")
    logger.setLevel(logging.WARNING)
    handler = logging.FileHandler(
        filename='discord.log', encoding='utf-8', mode='a')
    handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s Discord: %(funcName)s %(lineno)d: '
        '%(message)s',
        datefmt="[%d/%m/%Y %H:%M]"))
    logger.addHandler(handler)

    logger = logging.getLogger("yt")
    logger.setLevel(logging.INFO)

    yt_format = logging.Formatter(
        '%(asctime)s %(levelname)s YouTube Code: %(funcName)s %(lineno)d: '
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

@bot.command(aliases=["dpy"], pass_context=True)
async def updpy(ctx):
    if ctx.message.author.id == "116079569349378049":
        command = subprocess.Popen(["pip3", "install", "-U", "git+https://github.com/Rapptz/discord.py@master#egg=discord.py[voice]"], stdout=subprocess.PIPE)
        output = command.stdout.read().decode()
        await bot.say("```" + output + "```")
        if "Already up-to-date." not in output:
            await bot.say("Restarting now to apply changes...")
            session.close()
            await bot.logout()


@bot.command(aliases=["v"])
@commands.cooldown(1, 60, commands.BucketType.server)
async def version():
    """Shows the changelog and version of the bot"""
    msg = "```diff\n"
    msg += "- YouTube\n\n"
    #msg += "CURRENTLY TESTING\n"
    msg += "! Current Version: 1.5"
    msg += "\n\n"
    msg += "+ What's new?\n\n"
    msg += "! 1.5\n--- Massive cleanup of code. More organised. Added cooldown warnings (available by typing `yt cooldowns`). Added logging. Errors should mostly be gone.\n\n"
    msg += "! 1.4.3\n--- Added info command.\n\n"
    msg += "! 1.4\n--- Channel Search\n\n+ Shows the title & sub count of the channel\n+ Shows the description\n+ Shows the thumbnail (or tries to!)\n\n"
    msg += "```\n"
    msg += "View the full changelog here: <https://fishyfing.github.io>\n"
    # msg += "! 1.3.1 - 1.3.3\n--- Added cooldowns to commands and cleaned up messy bits of code.\n\n"
    # msg += "! 1.3\n--- Now Playing URL for Discord.FM\n\n"
    # msg += "! 1.2.1\n--- Inital aesthetics changes. New randomised ping messages.\n\n"
    # msg += "! 1.2\n--- Added video title and uploader when displaying video result, for when embeds are turned off.\n\n"
    # msg += "! 1.1\n--- Moved to the official YouTube search API\n\n"
    # msg += "! 1.0\n--- Initial release.```\n"
    msg += "For more info, ask for @\U0000200BFrancis#6565 on this server: http://mlyri.cz/discord"
    await bot.say(msg)

@bot.command(pass_context=True)
async def cooldowns(ctx):
    msg = "__Command cooldowns:__\n\n"
    msg += "Search: 5/60s per server\n"
    msg += "Channel: 5/60s per server\n"
    msg += "Version: 1/60s per server\n"
    msg += "Info: 1/60s per server\n"
    if ctx.message.server.id == '143686242687647745':
        msg += "Now playing: 30/600s\n"
    msg += "Stats: 1/300s per server"
    await bot.say(msg)

@bot.command()
@commands.cooldown(1, 60, commands.BucketType.server)
async def info():
    """Shows some info about this boat."""
    msg = "Hi there! I'm __**YouTube**__, a bot made by **@\U0000200BFrancis#6565**.\n\n"
    msg += "I'm made in Python using the `discord.py` library, and I'm here to interact with **YouTube via Discord**, so you don't have to.\n\n"
    msg += "__**What can I do?**__\n\n"
    msg += "- I can search YouTube for a video.\n- I can search YouTube for a channel.\n- I *can* do other stuff... But it's in testing!\n\nFor more info, join the MonsterLyrics server (http://mlyri.cz/discord) and ask for @\U0000200BFrancis#6565."
    await bot.say(msg)

@bot.command(aliases=["np"], no_pm=True, pass_context=True, hidden=True)
@commands.cooldown(30, 600, commands.BucketType.server)
async def nowplaying(ctx):
    """Show the currently playing song on Discord.FM. Only works there."""
    if ctx.message.server.id == '143686242687647745':
        channel = ctx.message.channel
        if (channel.id == '197142982686670848') or (channel.id == '143734628849549312'):
            await bot.say('Silly you. I can\'t get the URL of the song playing here!')
        else:
            try:
                url = 'https://temp.discord.fm/libraries/{}/queue'.format(channel)
                async with aiohttp.get(url) as r:
                    data = await r.json()
                song = data['current']
                if song['service'] == 'YouTubeVideo':
                    vid = song['identifier']
                    await bot.say('\N{BLACK RIGHT-POINTING TRIANGLE} Currently playing in __{}__: https://youtube.com/watch?v={}'.format(channel, vid))
                elif song['service'] == 'SoundCloudTrack':
                    track = song['identifier']
                    await bot.say('\N{BLACK RIGHT-POINTING TRIANGLE} Currently playing in __{}__: https://soundcloud.com/{}'.format(channel, track))
            except:
                await bot.say('Could not get Now Playing data or this is a new service. \N{EYES}')
                logger.exception('New Discord FM service found?')
    else:
        await bot.say("This isn't Discord.FM! <https://join.discord.fm>")

@bot.command(pass_context=True, aliases=["s"])
@commands.cooldown(5, 60, commands.BucketType.channel)
async def search(ctx):
    """Searches YouTube for a video. 

    Returns the first result."""
    try:
        await bot.send_typing(ctx.message.channel)
        if len(ctx.message.content.split(' ', 2)) == 2:
            msg = "Arguments needed!\n\nExample: `yt search Darude Sandstorm`"
        else:
            youtube = build("youtube", "v3", developerKey=key)
            search_response = youtube.search().list(q=ctx.message.content.split(' ', 2)[2],part="id,snippet",maxResults=1,type="video").execute()
            if len(search_response.get('items')) == 0:
                msg = "No videos found."
            else:
                vidid = search_response.get('items')[0]['id']['videoId']
                vidurl = "https://www.youtube.com/watch?v=" + vidid
                yt_url = "http://www.youtube.com/oembed?url={0}&format=json".format(vidurl)
                metadata = await get_json(yt_url)
                msg = '**Title:** _{}_\n**Uploader:** _{}_\n\n<{}>'.format(metadata['title'], metadata['author_name'], vidurl)
        await bot.say(msg)
    except Exception as e:
        message = 'The bass kicked too hard... :eyes: `{}` This has been reported.'.format(e)
        logger.exception(e)
        await bot.say(message)
        owner = discord.utils.get(bot.get_all_members(), id='116079569349378049')
        await bot.send_message(owner, 'Server: {}\n\nError in command `search` from id `{}`: {}\n\n'.format(ctx.message.server, vidid, e))

@bot.command(pass_context=True, aliases=["l"])
@commands.cooldown(5, 60, commands.BucketType.channel)
async def lookup(ctx):
    """Searches the DFM library for the song, and checks if it exists."""
    try:
        await bot.send_typing(ctx.message.channel)
        if len(ctx.message.content.split(' ', 2)) == 2:
            msg = "Arguments needed!\n\nExample: `yt lookup Darude Sandstorm`"
        else:
            youtube = build("youtube", "v3", developerKey=key)
            search_response = youtube.search().list(q=ctx.message.content.split(' ', 2)[2],part="id,snippet",maxResults=1,type="video").execute()
            if len(search_response.get('items')) == 0:
                msg = "No videos found."
            else:
                vidid = search_response.get('items')[0]['id']['videoId']
                vidurl = "https://www.youtube.com/watch?v=" + vidid
                yt_url = "http://www.youtube.com/oembed?url={0}&format=json".format(vidurl)
                metadata = await get_json(yt_url)
                title = metadata['title']
                try:
                    url = "https://temp.discord.fm/requests/json"
                    async with aiohttp.get(url) as r:
                        resp = await r.json()
                    lib = resp[1]
                    if title in resp[2][0]:
                        await bot.say("{} exists in the Discord.FM database for the library {}!".format(title, lib))
                except Exception as e:
                    message = 'The bass kicked too hard... :eyes: `{}` This has been reported to the creator.'.format(e)
                    logger.exception(e)
                    await bot.say(message)
                    owner = discord.utils.get(bot.get_all_members(), id='116079569349378049')
                    await bot.send_message(owner, 'Server: {}\n\nError in command `lookup` from id `{}`: {}\n\n'.format(ctx.message.server, vidid, e))
    except Exception as e:
        message = 'The bass kicked too hard... :eyes: `{}` This has been reported to the creator.'.format(e)
        logger.exception(e)
        await bot.say(message)
        owner = discord.utils.get(bot.get_all_members(), id='116079569349378049')
        await bot.send_message(owner, 'Server: {}\n\nError in command `lookup` from id `{}`: {}\n\n'.format(ctx.message.server, vidid, e))

@bot.command(pass_context=True, aliases=["c"])
@commands.cooldown(5, 60, commands.BucketType.channel)
async def channel(ctx):
    """Searches YouTube for a channel. 

    Returns the first result."""
    try:
        await bot.send_typing(ctx.message.channel)
        if len(ctx.message.content.split(' ', 2)) == 2:
            msg = "Arguments needed!\n\nExample: `yt channel TrapNation`"
        else:
            youtube = build("youtube", "v3", developerKey=key)
            search_response = youtube.search().list(q=ctx.message.content.split(' ', 2)[2],part="id,snippet",maxResults=1,type="channel").execute()
            if len(search_response.get('items')) == 0:
                msg = "No channels found."
            else:
                chanid = search_response.get('items')[0]['id']['channelId']
                data = youtube.channels().list(part='statistics,snippet', id=chanid).execute()
                subs = str(data['items'][0]['statistics']['subscriberCount'])
                name = str(data['items'][0]['snippet']['title'])
                img = str(data['items'][0]['snippet']['thumbnails']['default']['url'])
                chanurl = "https://www.youtube.com/channel/" + chanid
                msg = '**Channel:** {}\n**Subscribers:** {}\n<{}>\n\n**Thumbnail:** {}'.format(name, subs, chanurl, img)
        await bot.say(msg)
    except Exception as e:
        message = 'The bass kicked too hard... :eyes: `{}` This has been reported to the creator.'.format(e)
        logger.exception(e)
        await bot.say(message)
        owner = discord.utils.get(bot.get_all_members(), id='116079569349378049')
        await bot.send_message(owner, 'Server: {}\n\nError in command `channel` from id `{}`: {}\n\n'.format(ctx.message.server, chanid, e))

@bot.command(pass_context=True, aliases=['st'])
@commands.cooldown(5, 60, commands.BucketType.channel)
async def stats(ctx):
    """Reverse lookup for youtube videos. Returns statistics and stuff"""
    try:
        await bot.send_typing(ctx.message.channel)
        if len(ctx.message.content.split(' ', 2)) == 2:
            msg = "Arguments needed!\n\nExample: `yt stats https://www.youtube.com/watch?v=dQw4w9WgXcQ`"
        else:
            q=ctx.message.content.split(' ', 2)[2]
            yt_url = "http://www.youtube.com/oembed?url={0}&format=json".format(q)
            metadata = await get_json(yt_url)
            msg = '**Title:** _{}_\n**Uploader:** _{}_\n\n<{}>'.format(metadata['title'], metadata['author_name'], vidurl)
        await bot.say(msg)
    except Exception as e:
        message = 'The bass kicked too hard... :eyes: `{}` This has been reported.'.format(e)
        logger.exception(e)
        await bot.say(message)
        owner = discord.utils.get(bot.get_all_members(), id='116079569349378049')
        await bot.send_message(owner, 'Server: {}\n\nError in command `search` from id `{}`: {}\n\n'.format(ctx.message.server, vidid, e))


async def get_json(yt_url):
    """
    Returns the JSON from an URL.
    Expects the url to be valid and return a JSON object.
    """
    async with aiohttp.get(yt_url) as r:
        result = await r.json()
    return result

@bot.command(no_pm=True, hidden=True)
@commands.cooldown(1, 40, commands.BucketType.server)
async def ping():
    """Pong!"""
    choices = ["I'm alive...", "What do you want?", "Can't you see I'm sleeping here?", "Ugh. Is it Monday again?", "Time to remember the most important person here.", "You still suck.", "What's your name?"]
    await bot.say(randchoice(choices))

@bot.command(hidden=True, aliases=['bs'])
@commands.cooldown(1, 300, commands.BucketType.server)
async def botstats():
    """Server count"""
    users = str(len([m for m in set(bot.get_all_members())]))
    msg = "Servers: {}".format(len(list(bot.servers)))
    msg += "\nUsers: {}".format(users)
    # msg += "\n{} high quality videos searched.".format(search_count)
    # msg += "\n{} channels searched.".format(channel_count)
    up = abs(bot.uptime - int(time.perf_counter()))
    up = str(datetime.timedelta(seconds=up))
    msg += "\nUptime: {}".format(up)
    await bot.say(msg)

@bot.command(pass_context=True, hidden=True)
async def name(ctx, *, name):
    """Sets the bot's name"""
    if ctx.message.author.id == '116079569349378049':
        name = name.strip()
        if name != "":
            await bot.edit_profile(username=name)
            await bot.say("Done.")


@bot.command(pass_context=True, hidden=True)
async def status(ctx, *, status=None):
    """Sets the bot's status

    Leaving this empty will clear it. OWNER ONLY"""
    if ctx.message.author.id == '116079569349378049':
        if status:
            status = status.strip()
            await bot.change_status(discord.Game(name=status))
        else:
            await bot.change_status(None)
        await bot.say("Done.")

@bot.command(hidden=True)
async def avatar(url):
    """Sets the bot's avatar

    OWNER ONLY"""
    if ctx.message.author.id == '116079569349378049':
        async with bot.http.session.get(url) as r:
            data = await r.read()
        await bot.edit_profile(avatar=data)
        await bot.say("Done.")

@bot.command()
async def join():
    """Provides an OAuth link used to add the bot to the server."""
    msg = ("Use this link to add me to your server! Requires the `manage server` permission. https://is.gd/ytdiscord")
    await bot.say(msg)

@bot.command(name="shutdown", aliases=["sd"], no_pm=True, pass_context=True, hidden=True)
async def shutdown(ctx):
    """Stops the bot."""
    if ctx.message.author.id == '116079569349378049':
        await bot.say('Shutting down...')
        session.close()
        await bot.logout()

@bot.command(aliases=["gp"], hidden=True, pass_context=True)
async def update(ctx):
    if ctx.message.author.id == '116079569349378049':
        g = git.cmd.Git('/home/fishyfing/youtubebot')
        try:
            g.pull()
            await bot.say('Successfully updated.')
        except:
            await bot.say('Stashing changes...')
            g.stash()
            g.pull()
            await bot.say('Successfully updated...')

def main():
    set_logger()
    try:
        yield from bot.login('') 
        #login here
    except TypeError as e:
        logger.warning(e)
        msg = ("\nYou are using an outdated discord.py.\n"
               "update your discord.py with by running this in your cmd "
               "prompt/terminal.\npip3 install --upgrade git+https://"
               "github.com/Rapptz/discord.py@async")
        sys.exit(msg)
    yield from bot.connect()

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