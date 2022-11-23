import os
import json
import time
import discord
import requests
import stockBotConfig
from discord.ext import commands

accountsDir = "accounts/"

startingMoney = 10000

# how long should the script remember a price for before using the API to fetch the most recent price (seconds)
maxPriceAge = 600 # 10 minutes

# table of ticker prices and their ages
# used to save and reuse stock prices in the short term to save on API calls
priceCache = {}

class Account():
    def __init__(self, id, cashOnHand:int = startingMoney, portfolio:dict = {}) -> None:
        self.id = id
        self.cashOnHand = cashOnHand
        self.portfolio = portfolio

    def __str__(self) -> str:
        return json.dumps(self.__dict__, indent=4)

    def totalValue(self):
        value = self.cashOnHand
        for stock, quantity in self.portfolio:
            value += getPrice(stock) * quantity
        return value

    def save(self):
        with open(f"{accountsDir}{self.id}", "wt") as file:
            file.write(self.__str__())

def loadAccount(id:int):
    for file in os.listdir(accountsDir):
        if int(file) == id:
            f = open(f"{accountsDir}{file}")
            accData = json.load(f)
            f.close()
            acc = Account(**accData)
            return acc
    # if we made it past the loop that means no account exists with this ID
    # so make a new one
    print(f"making new account #{id}")
    acc = Account(id)
    acc.save()
    return acc


def getData(ticker:str = ""):
    ticker = ticker.upper()
    # qeuery the API
    data = requests.get(f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={ticker}&apikey={stockBotConfig.API_TOKEN}")
    obj = data.json()

    # check for rate limit error
    if "Note" in obj:
        return None

    obj = obj["Global Quote"]
    return obj

def getPrice(ticker:str = ""):
    ticker = ticker.upper()
    # search the price cache
    if ticker in priceCache:
        # check the age of the data
        # if the age of this price is less than the max, reuse it
        if time.time() - priceCache[ticker][1] < maxPriceAge:
            return priceCache[ticker][0]
    # otherwise get the price from the API
    data = getData(ticker)
    if not data:
        return None
    price = float(data["05. price"])
    return price

class Stocks(commands.Cog):

    def __init__(self, client) -> None:
        super().__init__()
        # check for accounts folder
        if not os.path.exists(accountsDir):
            os.makedirs(accountsDir)

    @commands.Cog.listener()
    async def on_ready(self):
        print("Stocks Cog is ready")

    @commands.command()
    async def price(self, ctx, ticker):
        price = self.getPrice(ticker)

        if not price:
            return await ctx.send("Rate limited or invalid ticker, please try again in 1 minute")
        
        return await ctx.send(f"({ticker.upper()}) current price: {price}")



def setup(client):
    client.add_cog(Stocks(client))