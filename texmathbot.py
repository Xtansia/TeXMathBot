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
import sys
import tempfile

# Settings

if 'DISCORD_TOKEN' not in os.environ:
    print('DISCORD_TOKEN environment variable must be set', file=sys.stderr)
    exit(1)

discord_token = os.environ['DISCORD_TOKEN']
command_prefix = os.environ.get('COMMAND_PREFIX', '%')
latex2png_url = os.environ.get('LATEX2PNG_URL', 'http://latex2png:8080/')

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


async def generate_latex_image(latex):
    async with aiohttp.ClientSession() as session:
        async with session.post(latex2png_url,
                                data=bytes(latex, 'utf8')) as resp:
            if resp.status == 200:
                img_filedesc, img_filename = tempfile.mkstemp(suffix='.png')

                with os.fdopen(img_filedesc, 'wb') as img_filehandle:
                    img_filehandle.write(await resp.read())

                return img_filename, None
            else:
                logger.error('Latex2PNG Error: %s' % await resp.text())

                if resp.status == 408:
                    return None, 'Timed Out'
                elif resp.status == 400:
                    return None, 'LaTeX Rendering Failed'
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


@bot.command(pass_context=True)
async def math(ctx, *, mathexpr: str):
    """Renders a LaTeX math expression to a PNG"""

    await bot.type()

    logger.info('[%s] math `%s`' % (ctx.message.id, mathexpr))
    latex = math_template.replace('__DATA__', mathexpr)

    img_filename, error_msg = await generate_latex_image(latex)

    if img_filename is not None:
        await respond(ctx.message, None, file=img_filename)
        os.remove(img_filename)
    else:
        await respond(ctx.message, 'Error [%s] : %s' % (mathexpr, error_msg))


logger = setup_logging('texmathbot', stdout_level=logging.INFO)
bot.run(discord_token)
