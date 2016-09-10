#!/usr/bin/env python3

"""
Copyright (c) 2016, Thomas Farr

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""

import aiohttp
import discord
from discord.ext import commands
import json
import os
import shutil
import sys
import tempfile
import uuid


### Settings ###

if 'DISCORD_TOKEN' not in os.environ:
  print('DISCORD_TOKEN environment variable must be set', file=sys.stderr)
  exit(1)

discord_token = os.environ['DISCORD_TOKEN']
command_prefix = os.environ.get('COMMAND_PREFIX', '%')
latex2png_url = os.environ.get('LATEX2PNG_URL', 'http://latex2png:8080/')

with open('math_template.latex') as math_template_fh:
  math_template = math_template_fh.read()


### Bot ###

bot_description = 'A bot that renders LaTeX math expressions to PNGs'
bot = commands.Bot(command_prefix=command_prefix, description=bot_description)


@bot.event
async def on_ready():
  print('Logged in as')
  print(bot.user.name)
  print(bot.user.id)
  print('----------')


@bot.command()
async def math(*, mathexpr: str):
  """Renders a LaTeX math expression to a PNG"""

  print('Math Expr: `%s`' % mathexpr)
  latex = math_template.replace('__DATA__', mathexpr)

  img_fn = None
  error_msg = None

  async with aiohttp.ClientSession() as session:
    async with session.post(latex2png_url, data=bytes(latex, 'UTF-8')) as resp:
      if resp.status == 200:
        img_fd, img_fn = tempfile.mkstemp(suffix='.png')
        with os.fdopen(img_fd, 'wb') as img_fh:
          img_fh.write(await resp.read())
      else:
        print('Error [%s] : %s' % (mathexpr, await resp.text()))
        if resp.status == 408:
          error_msg = 'Timed Out'
        elif resp.status == 400:
          error_msg = 'LaTeX Rendering Failed'
        else:
          error_msg = 'Unexpected Response : %03d - %s' % (
              resp.status, resp.reason)

  if img_fn is not None:
    await bot.upload(img_fn, filename=('%s.png' % (uuid.uuid4(),)))
    os.remove(img_fn)
  else:
    await bot.say('ERROR [%s] : %s' % (mathexpr, error_msg))


bot.run(discord_token)
