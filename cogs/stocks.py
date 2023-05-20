from discord.ext import commands
import yfinance as yf
import stockBotConfig
import discord
import time
import json
import os

# how many dollars does a new acount hove to start with
startingMoney = 10000

# how long should the script remember a price for before using the API to fetch the most recent price (seconds)
maxPriceAge = 0 # 0 seconds

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

        # the portfolio keeps track of the stocks owned and the money spent on a stock to keep track of returns
        # portfolio dictionary
        # {
        #     "ticker" : [quantity owned, money spent]

    def __str__(self) -> str:
        return json.dumps(self.__dict__, indent=4)

    def totalValue(self):
        value = self.cashOnHand
        for ticker, stockStats in self.portfolio.items():
            quantity, _ = stockStats
            value += getPrice(ticker) * quantity
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

def getPrice(symbol:str = ""):
    # search the price cache
    if symbol in priceCache:
        # check the age of the data
        # if the age of this price is less than the max, reuse it
        if time.time() - priceCache[symbol][1] < maxPriceAge:
            return priceCache[symbol][0]
    # otherwise get the price from yahoo finance
    ticker = yf.Ticker(symbol)
    if not ticker.info:
        return -1
    price = round(ticker.fast_info["last_price"], 2)
    # put this price into the cache for later use
    priceCache[symbol] = (price, time.time())
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
    async def price(self, ctx, ticker:str, quantity:int = 1):
        ticker = ticker.upper()
        price = getPrice(ticker)

        if not price:
            return await ctx.send("Could not gett ticker price, check the name and try again")
        if price < 0:
            return await ctx.send("Could not get ticker price, check the name and try again")
        
        totalPrice = price * quantity

        return await ctx.send(f"Price of {quantity} {ticker} shares: {totalPrice}")

    @commands.command()
    async def portfolio(self, ctx, member:discord.Member = None):
        if not member:
            member = ctx.author
        accountID = member.id
        acc = loadAccount(accountID)

        totalValue = acc.cashOnHand
        messageString = ""
        for ticker, stockStats in acc.portfolio.items():
            quantity, moneySpent = stockStats
            if quantity < 1:
                continue
            price = getPrice(ticker)
            value = price*quantity
            totalValue += value
            profit = round(value - moneySpent, 2)
            profitPercent = round(100 * profit / moneySpent, 2)
            profitString = "▲"*(profit > 0) + "▼"*(profit<0) + '${:.2f}'.format(profit) + f" ({'{:.2f}'.format(profitPercent)}%)"
            messageString += f"{ticker.ljust(6)} | {str(quantity).rjust(3)} | {'{:.2f}'.format(price).rjust(7)} | {'{:.2f}'.format(value).rjust(8)} | {profitString}\n"
        # prepend the header now that the total value is calculated
        messageString = f"```\nAccount ID:{acc.id}\nCash on hand ${acc.cashOnHand:.2f}\nTotal account value: ${totalValue:.2f}\n----------------------------------------\nticker | Qty |  price  |  $value  | profit\n" + messageString
        messageString += "```"
        return await ctx.send(messageString)

    @commands.command()
    async def buy(self, ctx, ticker:str, quantity:int = 1):
        ticker = ticker.upper()
        authorID = ctx.author.id
        account = loadAccount(authorID)
        price = getPrice(ticker)
        if price < 0:
            return await ctx.send("Could not get ticker price, check the name and try again")
        priceTotal = round(price * quantity, 2)

        # can the user afford this purchase
        if priceTotal > account.cashOnHand:
            return await ctx.send(f"You cannot afford to buy {quantity} shares of {ticker} (${priceTotal}). You only have (${account.cashOnHand})")

        # actually buying the shares
        account.cashOnHand += -priceTotal
        account.portfolio[ticker] = account.portfolio.get(ticker, [0, 0])
        # update the quantity owned
        account.portfolio[ticker][0] = account.portfolio[ticker][0] + quantity
        # update the total money spent on this stock
        account.portfolio[ticker][1] = account.portfolio[ticker][1] + priceTotal
        account.save()
        return await ctx.send(f"You have bought {quantity} shares of {ticker} for ${priceTotal}")

    @commands.command()
    async def sell(self, ctx, ticker:str, quantity:int = 1):
        ticker = ticker.upper()
        authorID = ctx.author.id
        account = loadAccount(authorID)
        # check if the user has enough shares
        account.portfolio[ticker] = account.portfolio.get(ticker, [0, 0])
        sharesOwned = account.portfolio[ticker][0]
        if quantity > sharesOwned:
            return await ctx.send(f"Cannot sell {quantity} shares of {ticker}, you only own {sharesOwned} shares")
        price = getPrice(ticker)
        if price < 0:
            return await ctx.send("Could not get ticker price, check the name and try again")
        priceTotal = round(price * quantity, 2)

        # actually selling the shares
        account.cashOnHand += priceTotal
        # update the quantity owned
        account.portfolio[ticker][0] = sharesOwned - quantity
        # update the total money spent on this stock
        account.portfolio[ticker][1] = account.portfolio[ticker][1] * (1 - (quantity / sharesOwned))
        account.save()
        return await ctx.send(f"You have sold {quantity} shares of {ticker} for ${priceTotal}")


async def setup(client):
    await client.add_cog(Stocks(client))