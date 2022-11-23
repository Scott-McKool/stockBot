import requests
from discord.ext import commands

class Stocks(commands.Cog):

    def __init__(self, client) -> None:
        super().__init__()

    @commands.Cog.listener()
    async def on_ready(self):
        print("Stocks Cog is ready")

    @commands.command()
    async def testy(self, ctx):
        await ctx.send("joe mama is huge")

def setup(client):
    client.add_cog(Stocks(client))