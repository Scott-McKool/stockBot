from discord.ext import commands
from datetime import datetime
from pytz import timezone
import yfinance as yf
import stockBotConfig
import discord
import time
import json
import os

# how many dollars does a new acount hove to start with
starting_money = 10000

# table of ticker prices and their ages
# used to save and reuse stock prices in the short term to save on API calls
# expire_time is a timestamp for when the data will be too old
#{
#  "ticker" : (price, expire_time),
#}
price_cache = {}

accounts_folder = stockBotConfig.BOT_DIR+"accounts/"

def is_market_open() -> bool:
    # get the current time in us est timezone 
    dt = datetime.now(timezone('US/Eastern'))
    # market is open on weekdays (days 0-4) between 9:30 am and 4:00 pm
    return 0 <= dt.weekday() <= 4 and 9*60+30 <= dt.hour*60+dt.minute <= 16*60

def loadAccount(id:int, guild_id:int):
    # if a dir does not exits for this guild
    if not os.path.exists(f"{accounts_folder}{guild_id}"):
        # make one
        os.makedirs(f"{accounts_folder}{guild_id}")
    # save account info under a file with the user id in a directory of the guild id
    for file in os.listdir(f"{accounts_folder}{guild_id}"):
        if int(file) == id:
            with open(f"{accounts_folder}{guild_id}/{file}") as account_file:
                account_data = json.load(account_file)
            acc = Account(**account_data)
            return acc
    # if past the loop that means no account exists with this ID
    # so make a new one
    print(f"making new account #{id}")
    acc = Account(id, guild_id)
    acc.save()
    return acc

def getPrice(symbol:str):
    symbol = symbol.upper()
    # search the price cache
    if symbol in price_cache:
        # if the price has not expired yet
        if time.time() < price_cache[symbol][1]:
            return price_cache[symbol][0]
    # otherwise get the price from yahoo finance
    ticker = yf.Ticker(symbol)
    price = -1
    try:
        price = round(ticker.fast_info["last_price"], 2)
    except:
        return -1
    # put this price into the cache for later use
    price_cache[symbol] = (price, time.time() + 60)
    return price


class Account():
    def __init__(self, id, guild_id: str, cash_on_hand:int = starting_money, portfolio:dict = {}) -> None:
        # user id
        self.id = str(id)
        # the guild (server) this accound belongs in
        self.guild_id = str(guild_id)
        # how many dollars does this accound have available to spend
        self.cash_on_hand = cash_on_hand
        # the portfolio keeps track of the stocks owned and the money spent on a stock to keep track of returns
        # portfolio dictionary
        # {
        #     "ticker" : [quantity owned, money spent]
        self.portfolio = portfolio

    def __str__(self) -> str:
        return json.dumps(self.__dict__, indent=4)

    def save(self):
        # if a dir does not exits for this guild
        if not os.path.exists(f"{accounts_folder}{self.guild_id}"):
            # make one
            os.makedirs(f"{accounts_folder}{self.guild_id}")
        with open(f"{accounts_folder}{self.guild_id}/{self.id}", "wt") as file:
            file.write(self.__str__())

    def total_value(self):
        value = self.cash_on_hand
        for ticker, cash_on_hand in self.portfolio.items():
            quantity, _ = cash_on_hand
            price = getPrice(ticker)
            if price == -1:
                continue
            value += getPrice(ticker) * quantity
        return round(value, 2)

class Stocks(commands.Cog):

    def __init__(self, client) -> None:
        super().__init__()
        # check for accounts folder
        if not os.path.exists(accounts_folder):
            os.makedirs(accounts_folder)

    @commands.Cog.listener()
    async def on_ready(self):
        print("Stocks Cog is ready")

    @commands.command()
    async def price(self, ctx, ticker:str, quantity:int = 1):
        ticker = ticker.upper()
        price = getPrice(ticker)

        if price < 0:
            return await ctx.send("Could not get ticker price, check the name and try again")
        
        total_price = round(price * quantity, 2)

        return await ctx.send(f"Price of {quantity} {ticker} shares: {total_price:.2f}")

    @commands.command()
    async def portfolio(self, ctx, member:discord.Member = None):
        if not member:
            member = ctx.author
        account_id = member.id
        guild_id = ctx.guild.id
        acc = loadAccount(account_id, guild_id)

        total_value = acc.cash_on_hand
        message_string = ""
        for ticker, cash_on_hand in acc.portfolio.items():
            quantity, money_spent = cash_on_hand
            if quantity < 1:
                continue
            price = getPrice(ticker)
            if price == -1:
                continue
            value = price*quantity
            total_value += value
            profit = round(value - money_spent, 2)
            profit_percent = round(100 * profit / money_spent, 2)
            profit_string = "▲"*(profit > 0) + "▼"*(profit<0) + '${:.2f}'.format(profit) + f" ({'{:.2f}'.format(profit_percent)}%)"
            message_string += f"{ticker.ljust(8)} | {str(quantity).rjust(6)} | {'{:.2f}'.format(price).rjust(8)} | {'{:.2f}'.format(value).rjust(9)} | {profit_string}\n"
        # prepend the header now that the total value is calculated
        message_string = f"```\nAccount ID:{acc.id}\nCash on hand ${acc.cash_on_hand:.2f}\nTotal account value: ${total_value:.2f}\n----------------------------------------\nticker   |   Qty  |  price   |  $value   | profit\n" + message_string
        message_string += "```"
        return await ctx.send(message_string)

    @commands.command()
    async def buy(self, ctx, ticker:str, quantity:int = 1):
        ticker = ticker.upper()
        author_id = ctx.author.id
        guild_id = ctx.guild.id
        account = loadAccount(author_id, guild_id)
        price = getPrice(ticker)
        if price < 0:
            return await ctx.send("Could not get ticker price, check the name and try again")
        price_total = round(price * quantity, 2)

        # can the user afford this purchase
        if price_total > account.cash_on_hand:
            return await ctx.send(f"You cannot afford to buy {quantity} shares of {ticker} (${price_total}). You only have (${account.cash_on_hand})")

        # actually buying the shares
        account.cash_on_hand += -price_total
        account.portfolio[ticker] = account.portfolio.get(ticker, [0, 0])
        # update the quantity owned
        account.portfolio[ticker][0] = account.portfolio[ticker][0] + quantity
        # update the total money spent on this stock
        account.portfolio[ticker][1] = account.portfolio[ticker][1] + price_total
        account.save()
        return await ctx.send(f"You have bought {quantity} shares of {ticker} for ${price_total}")

    @commands.command()
    async def sell(self, ctx, ticker:str, quantity:int = 1):
        ticker = ticker.upper()
        author_id = ctx.author.id
        guild_id = ctx.guild.id
        account = loadAccount(author_id, guild_id)
        # check if the user has enough shares
        account.portfolio[ticker] = account.portfolio.get(ticker, [0, 0])
        shares_owned = account.portfolio[ticker][0]
        if quantity > shares_owned:
            return await ctx.send(f"Cannot sell {quantity} shares of {ticker}, you only own {shares_owned} shares")
        price = getPrice(ticker)
        if price < 0:
            return await ctx.send("Could not get ticker price, check the name and try again")
        price_total = round(price * quantity, 2)

        # actually selling the shares
        account.cash_on_hand += price_total
        # update the quantity owned
        account.portfolio[ticker][0] = shares_owned - quantity
        # update the total money spent on this stock
        account.portfolio[ticker][1] = account.portfolio[ticker][1] * (1 - (quantity / shares_owned))
        account.save()
        return await ctx.send(f"You have sold {quantity} shares of {ticker} for ${price_total}")


async def setup(client):
    await client.add_cog(Stocks(client))