"""
Copyright (c) 2016, Thomas Farr

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""

import aiohttp
from discord.ext import commands
import logging
import os
import re
import sys
import tempfile

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


async def respond(message, text, file=None):
    msg_id = '%s#%s' % (message.channel.id, message.id)

    if msg_id in responses:
        logger.info('Found old response: %s' % responses[msg_id])
        await bot.delete_message(
            await bot.get_message(message.channel, responses[msg_id]))

    if file is not None:
        resp = await bot.upload(file, filename='%s.%s' % (
            message.id, file[file.rfind('.') + 1:]), content=text)
    else:
        resp = await bot.say(text)

    responses[msg_id] = resp.id


@bot.event
async def on_ready():
    logger.info('Logged in as %s [%s]' % (bot.user.name, bot.user.id))
    for server in bot.servers:
        logger.info('In server %s [%s]' % (server.name, server.id))


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
async def on_message_delete(message):
    logger.info('Message Deleted [%s] : `%s`' % (message.id, message.content))
    msg_id = '%s#%s' % (message.channel.id, message.id)
    if msg_id in responses:
        logger.info('Found old response: %s' % responses[msg_id])
        await bot.delete_message(
            await bot.get_message(message.channel, responses[msg_id]))


@bot.command(pass_context=True)
async def math(ctx, *, mathexpr: str):
    """Renders a LaTeX math expression to a PNG"""

    await bot.type()

    logger.info('[%s] math `%s`' % (ctx.message.id, mathexpr))
    latex = math_template.replace('__DATA__', mathexpr)

    img_filename, error_msg = await pngify('latex', latex)

    if img_filename is not None:
        await respond(ctx.message, None, file=img_filename)
        os.remove(img_filename)
    else:
        await respond(ctx.message, 'Error [%s] : %s' % (mathexpr, error_msg))


abc_field_pattern = re.compile(r"^([A-Z]):(.+)$")


@bot.command(pass_context=True)
async def music(ctx, *, tune: str):
    """Renders an ABC notation tune to a PNG"""

    await bot.type()
    logger.info('[%s] music `%s`' % (ctx.message.id, tune))

    abc_headers = {
        'M': '4/4',
        'L': '1/4',
        'K': 'Cmaj'
    }
    abc_notes = ''

    lines = tune.split('\n')
    i = 0
    while i < len(lines):
        match = abc_field_pattern.match(lines[i])
        if match is not None:
            abc_headers[match.group(1)] = match.group(2)
            if match.group(1) == 'K':
                break
        else:
            break
        i += 1

    while i < len(lines):
        abc_notes += lines[i] + '\n'
        i += 1

    abc = 'X:1\n'

    for field in filter(lambda f: f not in ['X','K'], abc_headers.keys()):
        abc += '%s:%s\n' % (field, abc_headers[field])

    abc += 'K:%s\n' % abc_headers['K']
    abc += abc_notes

    img_filename, error_msg = await pngify('abc', abc)

    if img_filename is not None:
        await respond(ctx.message, None, file=img_filename)
        os.remove(img_filename)
    else:
        await respond(ctx.message, 'Error [%s] : %s' % (tune, error_msg))


@bot.command(pass_context=True)
async def gplot(ctx, *, program: str):
    """Renders Gnuplot to a PNG"""

    await bot.type()
    logger.info('[%s] plot `%s`' % (ctx.message.id, program))

    img_filename, error_msg = await pngify('gnuplot', program)

    if img_filename is not None:
        await respond(ctx.message, None, file=img_filename)
        os.remove(img_filename)
    else:
        await respond(ctx.message, 'Error [%s] : %s' % (program, error_msg))


logger = setup_logging('texmathbot', stdout_level=logging.INFO)
bot.run(discord_token)
