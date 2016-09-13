# TexMathBot
A Discord bot that renders LaTeX math expressions to PNGs.

## Settings
Settings are set via the following environment variables.
- `DISCORD_TOKEN` is the login token for the bot user, and is required.
- `COMMAND_PREFIX` is the prefix for the commands, defaults to `%`.
- `PNGIFIER_URL` is a URL pointing to an instance of [pngifier](https://github.com/Xtansia/docker-pngifier), defaults to `http://pngifier:8080/` (ie. assumes that pngifier has been linked into the docker container as pngifier).
