import os
import json
import time
import discord
import requests
import stockBotConfig
from discord.ext import commands

# how many dollars does a new acount hove to start with
startingMoney = 10000

# how long should the script remember a price for before using the API to fetch the most recent price (seconds)
maxPriceAge = 600 # 10 minutes

# table of ticker prices and their ages
# used to save and reuse stock prices in the short term to save on API calls
#{
#  "ticker" : (price, timestamp),
#}
priceCache = {}

accountsDir = stockBotConfig.BOT_DIR+"accounts/"

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
    # if past the loop that means no account exists with this ID
    # so make a new one
    print(f"making new account #{id}")
    acc = Account(id)
    acc.save()
    return acc


def getData(ticker:str = ""):
    # qeuery the API
    data = requests.get(f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={ticker}&apikey={stockBotConfig.API_TOKEN}")
    obj = data.json()

    # check for rate limit error
    if "Note" in obj:
        return None

    obj = obj["Global Quote"]
    return obj

def getPrice(ticker:str = ""):
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
    # put this price into the cache for later use
    priceCache[ticker] = (price, time.time())
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
    async def price(self, ctx, ticker:str):
        ticker = ticker.upper()
        price = getPrice(ticker)

        if not price:
            return await ctx.send("Could not gett ticker price, check the ticker and try again in 1 minute")
        
        return await ctx.send(f"({ticker}) current price: {price}")

    @commands.command()
    async def portfolio(self, ctx, member:discord.member = None):
        if not member:
            member = ctx.author
        accountID = member.id
        acc = loadAccount(accountID)
        return await ctx.send(str(acc))

    @commands.command()
    async def buy(self, ctx, ticker:str, quantity:int = 1):
        ticker = ticker.upper()
        authorID = ctx.author.id
        account = loadAccount(authorID)
        price = getPrice(ticker)
        if not price:
            return await ctx.send("Could not gett ticker price, check the ticker and try again in 1 minute")
        priceTotal = price * quantity

        # can the user afford this purchase
        if priceTotal > account.cashOnHand:
            return await ctx.send(f"You cannot afford to buy {quantity} shares of {ticker} (${priceTotal}). You only have (${account.cashOnHand})")

        # actually buying the shares
        account.cashOnHand += -priceTotal
        account.portfolio[ticker] = account.portfolio.get(ticker, 0) + quantity
        account.save()
        return await ctx.send(f"You have bought {quantity} shares of {ticker} for ${priceTotal}")

    @commands.command()
    async def sell(self, ctx, ticker:str, quantity:int = 1):
        ticker = ticker.upper()
        authorID = ctx.author.id
        account = loadAccount(authorID)
        # check if the user has enough shares
        sharesOwned = account.portfolio.get(ticker, 0)
        if quantity > sharesOwned:
            return await ctx.send(f"Cannot sell {quantity} shares of {ticker}, you only own {sharesOwned} shares")
        price = getPrice(ticker)
        priceTotal = price * quantity

        # actually selling the shares
        account.cashOnHand += priceTotal
        account.portfolio[ticker] = account.portfolio.get(ticker, 0) - quantity
        account.save()
        return await ctx.send(f"You have sold {quantity} shares of {ticker} for ${priceTotal}")


def setup(client):
    client.add_cog(Stocks(client))