import requests
import stockBotConfig
from discord.ext import commands

class Stocks(commands.Cog):

    def __init__(self, client) -> None:
        super().__init__()

    def getData(self, ticker:str = ""):
        ticker = ticker.upper()

        data = requests.get(f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={ticker}&apikey={stockBotConfig.API_TOKEN}")

        obj = data.json()

        if "Note" in obj:
            print("rate limited")
            return None

        obj = obj["Global Quote"]
        return obj

    def getPrice(self, ticker:str = ""):
        data = self.getData(ticker)
        if not data:
            return None
        price = data["05. price"]
        return price

    @commands.Cog.listener()
    async def on_ready(self):
        print("Stocks Cog is ready")

    @commands.command()
    async def price(self, ctx, ticker):
        price = self.getPrice(ticker)

        if not price:
            return await ctx.send("Rate limited, please try again in 1 minute")
        
        return await ctx.send(f"({ticker.upper()}) current price: {price}")

def setup(client):
    client.add_cog(Stocks(client))