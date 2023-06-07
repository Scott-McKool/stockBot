from discord.ext import commands
import stockBotConfig
import discord
import asyncio
import urllib
import time
import os

bot = commands.Bot(command_prefix=stockBotConfig.PREFIX, intents=discord.Intents.default())

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
while(True):
    try:
        # will throw an error if not on internet
        urllib.request.urlopen("http://google.com")
    except Exception as e:
        print("did not log in, not connected to internet, retrying in 10 seconds. . .")
        time.sleep(10)
        continue
    bot.run(stockBotConfig.DISCORD_TOKEN)
    break