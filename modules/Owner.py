import discord
from discord.ext import commands
from modules.utils import checks
import inspect
import os
import logging
import traceback
import importlib
import asyncio


class Owner:
    """Owner Commands"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=['eval'], hidden=True)
    @checks.is_owner()
    async def debug(self, ctx, *, code: str):
        """Evaluates code."""
        code = code.strip('` ')
        python = '```py\n{}\n```'

        env = {
            'bot': self.bot,
            'ctx': ctx,
            'message': ctx.message,
            'guild': ctx.guild,
            'channel': ctx.channel,
            'author': ctx.author
        }

        env.update(globals())

        try:
            result = eval(code, env)
            if inspect.isawaitable(result):
                result = await result
        except Exception as e:
            await ctx.send(python.format(type(e).__name__ + ': ' + str(e)))
            return

        await ctx.send(python.format(result))

    @checks.is_owner()
    @commands.command(name="reload", aliases=['rl'], hidden=True)
    async def _reload(self, *, cog_name: str):
        """Reloads a module
        Example: reload audio"""
        module = cog_name.strip()
        if "modules." not in module:
            module = "modules." + module

        try:
            self._unload_cog(module, reloading=True)
        except:
            pass

        try:
            self._load_cog(module)
        except CogNotFoundError:
            await ctx.send("That cog cannot be found.")
        except NoSetupError:
            await ctx.send("That cog does not have a setup function.")
        except CogLoadError as e:
            logger.exception(e)
            traceback.print_exc()
            await ctx.send("That cog could not be loaded. Check your"
                           " console or logs for more information.")
        else:
            set_cog(module, True)
            await self.disable_commands()
            await ctx.send("The cog has been reloaded.")

    @commands.command(hidden=True)
    @checks.is_owner()
    async def load(self, *, cog_name: str):
        """Loads a module
        Example: load mod"""
        module = cog_name.strip()
        if "modules." not in module:
            module = "modules." + module
        try:
            self._load_cog(module)
        except CogNotFoundError:
            await ctx.send("That cog could not be found.")
        except CogLoadError as e:
            logger.exception(e)
            traceback.print_exc()
            await ctx.send("There was an issue loading the cog. Check"
                           " your console or logs for more information.")
        except Exception as e:
            logger.exception(e)
            traceback.print_exc()
            await ctx.send('Cog was found and possibly loaded but '
                           'something went wrong. Check your console '
                           'or logs for more information.')
        else:
            set_cog(module, True)
            await self.disable_commands()
            await ctx.send("The cog has been loaded.")

    @commands.command(hidden=True)
    @checks.is_owner()
    async def unload(self, *, cog_name: str):
        """Unloads a module
        Example: unload mod"""
        module = cog_name.strip()
        if "modules." not in module:
            module = "modules." + module
        if not self._does_cogfile_exist(module):
            await ctx.send("That cog file doesn't exist. I will not"
                           " turn off autoloading at start just in case"
                           " this isn't supposed to happen.")
        else:
            set_cog(module, False)
        try:  # No matter what we should try to unload it
            self._unload_cog(module)
        except OwnerUnloadWithoutReloadError:
            await ctx.send("I cannot allow you to unload the Owner plugin"
                           " unless you are in the process of reloading.")
        except CogUnloadError as e:
            logger.exception(e)
            traceback.print_exc()
            await ctx.send('Unable to safely unload that cog.')
        else:
            await ctx.send("The cog has been unloaded.")

    @commands.command(hidden=True)
    @checks.is_owner()
    async def announcement(self, ctx, *, message: str):
        """send a msg to ALL guilds."""
        guilds = list(self.bot.guilds)
        for guild in guilds:
            try:
                await guild.default_channel.send(message)
            except discord.Forbidden:
                continue
            finally:
                print('Sent message to {}'.format(guild.name.encode('utf-8')))
                await asyncio.sleep(15)

    def _load_cog(self, cogname):
        if not self._does_cogfile_exist(cogname):
            raise CogNotFoundError(cogname)
        try:
            mod_obj = importlib.import_module(cogname)
            importlib.reload(mod_obj)
            self.bot.load_extension(mod_obj.__name__)
        except SyntaxError as e:
            raise CogLoadError(*e.args)
        except:
            raise

    def _unload_cog(self, cogname, reloading=False):
        if not reloading and cogname == "modules.Owner":
            raise OwnerUnloadWithoutReloadError(
                "Can't unload the owner plugin :P")
        try:
            self.bot.unload_extension(cogname)
        except:
            raise CogUnloadError

    def _list_cogs(self):
        cogs = [os.path.basename(f) for f in glob.glob("modules/*.py")]
        return ["modules." + os.path.splitext(f)[0] for f in cogs]

    def _does_cogfile_exist(self, module):
        if "modules." not in module:
            module = "modules." + module
        if module not in self._list_cogs():
            return False
        return True


def setup(bot):
    global logger
    logger = logging.getLogger('yt')
    bot.add_cog(Owner(bot))
