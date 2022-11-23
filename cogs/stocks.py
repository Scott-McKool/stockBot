import os
import discord
import requests
import stockBotConfig
from discord.ext import commands
import json

accountsDir = stockBotConfig.BOT_DIR+"accounts/"

startingMoney = 10000

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
        with open(f"{accountsDir}{self.id}.json", "wt") as file:
            file.write(self.__str__())

def loadAccount(id:int):
    for file in os.listdir(accountsDir):
        if file == id:
            f = open("12345")
            accData = json.load(f)
            f.close()
            acc = Account(**accData)
            return acc
    # if we made it past the loop that means no account exists with this ID
    # so make a new one
    print(f"making new account #{id}")
    acc = Account(id)
    return acc


def getData(ticker:str = ""):
    ticker = ticker.upper()
    # qeuery the API
    data = requests.get(f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={ticker}&apikey={stockBotConfig.API_TOKEN}")

    obj = data.json()
    print(obj)
    # check for rate limit error
    if "Note" in obj:
        return None

    obj = obj["Global Quote"]
    return obj

def getPrice(ticker:str = ""):
    data = getData(ticker)
    if not data:
        return None
    price = data["05. price"]
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