from discord.ext import commands
from requests import get as get_request
import stockBotConfig
import discord
import asyncio
import urllib
import time
import os

bot = commands.Bot(command_prefix=stockBotConfig.PREFIX, intents=discord.Intents.all())

@bot.event
async def on_ready():
    print("stockBot ready")

@bot.command()
async def ping(ctx):
    '''
    Gets stockBot's latency 
    '''
    await ctx.send(f"pong {round(bot.latency*1000)}ms")

# load the cogs for this bot
for file_name in os.listdir(f"{stockBotConfig.BOT_DIR}cogs"):
    if(file_name.endswith(".py")):
        asyncio.run(bot.load_extension(f"cogs.{file_name[:-3]}"))

# wait till an internet connection is established before trying to login
#TODO this is kind of a hack-y solution, find a better way of running code when internet access is gained

has_connection = False
while(not has_connection):
    if (get_request("https://google.com").status_code == 200):
        has_connection = True
        break
    print("did not log in, not connected to internet, retrying in 10 seconds. . .")
    time.sleep(10)

bot.run(stockBotConfig.DISCORD_TOKEN)