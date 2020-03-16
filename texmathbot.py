"""
Copyright (c) 2016, Thomas Farr

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""

import aiohttp
from discord.ext import commands
import discord
import logging
import os
import re
import sys
import tempfile
from typing import Optional

# Settings

if 'DISCORD_TOKEN' not in os.environ:
    print('DISCORD_TOKEN environment variable must be set', file=sys.stderr)
    exit(1)

discord_token = os.environ['DISCORD_TOKEN']
command_prefix = os.environ.get('COMMAND_PREFIX', '%')
pngifier_url = os.environ.get('PNGIFIER_URL', 'http://pngifier:8080/')

if not os.path.isfile('math_template.latex'):
    print('math_template.latex must exist', file=sys.stderr)
    exit(1)

with open('math_template.latex') as math_template_filehandle:
    math_template = math_template_filehandle.read()


# Functions

def setup_logging(logger_name, stdout_level=logging.WARN):
    formatter = logging.Formatter(
        '%(asctime)s:%(levelname)s:%(name)s: %(message)s')

    file_handler = logging.FileHandler(filename='%s.log' % logger_name,
                                       encoding='utf8', mode='w')
    file_handler.setFormatter(formatter)

    stdout_handler = logging.StreamHandler(stream=sys.stdout)
    stdout_handler.setFormatter(formatter)
    stdout_handler.setLevel(stdout_level)

    discord_logger = logging.getLogger('discord')
    discord_logger.setLevel(logging.DEBUG)
    discord_logger.addHandler(file_handler)
    discord_logger.addHandler(stdout_handler)

    my_logger = logging.getLogger(logger_name)
    my_logger.setLevel(logging.DEBUG)
    my_logger.addHandler(file_handler)
    my_logger.addHandler(stdout_handler)

    return my_logger


async def pngify(source_format, content):
    async with aiohttp.ClientSession() as session:
        async with session.post(pngifier_url + source_format,
                                data=bytes(content, 'utf8')) as resp:
            if resp.status == 200:
                file_descriptor, file_name = tempfile.mkstemp(suffix='.png')
                with os.fdopen(file_descriptor, 'wb') as file_handle:
                    file_handle.write(await resp.read())
                return file_name, None
            else:
                logger.error('PNGifier Error: %s' % await resp.text())

                if resp.status == 408:
                    return None, 'Timed Out'
                elif resp.status == 400:
                    return None, 'Rendering Failed'
                else:
                    return None, 'Unexpected Response: %03d - %s' % (
                        resp.status, resp.reason)


# Bot

bot = commands.Bot(command_prefix=command_prefix,
                   pm_help=True,
                   description='A bot that renders LaTeX math expressions to '
                               'PNGs')
responses = {}


async def respond(ctx: commands.Context, text: Optional[str], file: str = None):
    msg_id = '%s#%s' % (ctx.channel.id, ctx.message.id)

    if msg_id in responses:
        logger.info('Found old response: %s' % responses[msg_id])
        old_resp: discord.Message = await ctx.fetch_message(responses[msg_id])
        await old_resp.delete()

    if file is not None:
        resp = await ctx.send(text, file=discord.File(file, filename='%s.%s' % (ctx.message.id, file[file.rfind('.') + 1:])))
    else:
        resp = await ctx.send(text)

    responses[msg_id] = resp.id


@bot.event
async def on_ready():
    logger.info('Logged in as %s [%s]' % (bot.user.name, bot.user.id))
    for guild in bot.guilds:
        logger.info('In guild %s [%s]' % (guild.name, guild.id))


@bot.event
async def on_server_join(server):
    logger.info('Joined server %s [%s]' % (server.name, server.id))


@bot.event
async def on_server_remove(server):
    logger.info('Left server %s [%s]' % (server.name, server.id))


@bot.event
async def on_message_edit(before, after):
    logger.info('Message Edited [%s] : `%s` => `%s`' % (
        before.id, before.content, after.content))
    await bot.process_commands(after)


@bot.event
async def on_message_delete(message: discord.Message):
    logger.info('Message Deleted [%s] : `%s`' % (message.id, message.content))
    channel: discord.TextChannel = message.channel
    msg_id = '%s#%s' % (channel.id, message.id)
    if msg_id in responses:
        logger.info('Found old response: %s' % responses[msg_id])
        resp_msg = await channel.fetch_message(responses[msg_id])
        await resp_msg.delete()


@bot.command()
async def math(ctx: commands.Context, *, mathexpr: str):
    """Renders a LaTeX math expression to a PNG"""

    async with ctx.typing():
        logger.info('[%s] math `%s`' % (ctx.message.id, mathexpr))
        latex = math_template.replace('__DATA__', mathexpr)

        img_filename, error_msg = await pngify('latex', latex)

        if img_filename is not None:
            await respond(ctx, None, file=img_filename)
            os.remove(img_filename)
        else:
            await respond(ctx, 'Error [%s] : %s' % (mathexpr[:50], error_msg))


abc_field_pattern = re.compile(r"^([A-Z]):(.+)$")


@bot.command()
async def music(ctx: commands.Context, *, tune: str):
    """Renders an ABC notation tune to a PNG"""

    async with ctx.typing():
        logger.info('[%s] music `%s`' % (ctx.message.id, tune))

        lines = tune.split('\n')

        if abc_field_pattern.match(lines[0]) is None:
            tune = 'X:1\nM:4/4\nL:1/4\nK:Cmaj\n' + tune

        img_filename, error_msg = await pngify('abc', tune)

        if img_filename is not None:
            await respond(ctx, None, file=img_filename)
            os.remove(img_filename)
        else:
            await respond(ctx, 'Error [%s] : %s' % (tune[:50], error_msg))


@bot.command()
async def gplot(ctx: commands.Context, *, program: str):
    """Renders Gnuplot to a PNG"""

    async with ctx.typing():
        logger.info('[%s] plot `%s`' % (ctx.message.id, program))

        img_filename, error_msg = await pngify('gnuplot', program)

        if img_filename is not None:
            await respond(ctx, None, file=img_filename)
            os.remove(img_filename)
        else:
            await respond(ctx, 'Error [%s] : %s' % (program[:50], error_msg))


logger = setup_logging('texmathbot', stdout_level=logging.INFO)
bot.run(discord_token)
