# discord-texmath
A Discord bot that renders LaTeX math expressions to PNGs.

## Settings
Settings are set via the following environment variables.
- `DISCORD_TOKEN` is the login token for the bot user, and is required.
- `COMMAND_PREFIX` is the prefix for the commands, defaults to `%`.
- `LATEX2PNG_URL` is a URL pointing to an instance of [latex2png](https://github.com/Xtansia/docker-latex2png), defaults to `http://latex2png:8080/` (ie. assumes that latex2png has been linked into the docker container as latex2png).