import os
import random

import discord
from discord.ext import commands
from dotenv import load_dotenv
import calendar_work
import discord_bot
from datetime import datetime
import parsedatetime as pdt

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

client = discord.Client(intents=discord.Intents.all())

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)

cal = pdt.Calendar()


@bot.event
async def on_ready():
    print(f'{bot.user.name} has connected to Discord!')


# Setup for sending a date and message from a mention to google calendar and chatbot algorithm respectively.
@bot.event
async def on_message(message):
    if message.author == client.user:
        return
    if message.mentions:
        mentions_string = str(message.mentions[0])
        mentions_real = bot.get_user(message.mentions[0].id)
        start_message = message.content
        now = datetime.now().replace(microsecond=0)
        reply = (f"%s" % (cal.parseDT(str(start_message), now)[0]))
        if str(reply) != str(now):
            await calendar_work.search_calendar(mentions_string, reply, mentions_real)
            return
        bot_answer = await discord_bot.bot_response(start_message)
        bot_answer = random.sample(bot_answer, 3)
        await mentions_real.send(f"Choose a reply!\n1. {bot_answer[0]}\n2. {bot_answer[1]}\n3. {bot_answer[2]}")
        response = await bot.wait_for("message", timeout=100)
        response = int(response.content)
        if bot_answer[response - 1].startswith("Yes"):
            await mentions_real.send("How long will the event be?")
            event_length = await bot.wait_for("message", timeout=100)
            await mentions_real.send("What would you like to name the event?")
            event_name = await bot.wait_for("message", timeout=100)
            await calendar_work.add_event(reply, event_length, event_name, mentions_real)
        await message.channel.send(f"{bot_answer[response - 1]}")
    await bot.process_commands(message)


# Command for getting user's credentials for their Google calendar:
@bot.command(name='calendar')
async def calendar_creds(ctx):
    author = str(ctx.message.author)
    author2 = ctx.message.author
    await calendar_work.get_credentials(bot, discord.Embed(), author, author2)


@bot.command(name='add')
async def add_event(ctx, day, time, length, *summary):
    author = ctx.message.author
    date = day + " " + time
    now = datetime.now().replace(microsecond=0)
    start = (f"%s" % (cal.parseDT(str(date), now)[0]))
    await calendar_work.add_event(start, length, summary, author)


# Command for starting a conversation with the bot
@bot.command(name='chatbot')
async def chatbot(ctx):
    await discord_bot.user_input_output(ctx, bot)


bot.run(TOKEN)
