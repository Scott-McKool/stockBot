import stockBotConfig
import os
import urllib
import time
import discord
from discord.ext import commands

coolIntents = discord.Intents.default()
coolIntents.members = True

bot = commands.Bot(command_prefix=stockBotConfig.PREFIX, intents=coolIntents)

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
for filename in os.listdir(f"{stockBotConfig.BOT_DIR}cogs"):
    if(filename.endswith(".py")):
        bot.load_extension(f"cogs.{filename[:-3]}")

# wait till an internet connection is established before trying to login
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