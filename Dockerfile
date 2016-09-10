FROM python:3.5

RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app

RUN pip install discord.py

ADD texmathbot.py math_template.latex /usr/src/app/

CMD python texmathbot.py