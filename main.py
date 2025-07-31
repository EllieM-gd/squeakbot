import discord
from discord.ext import commands
import logging
from dotenv import load_dotenv
import os
import random
import webserver

load_dotenv()
token = os.getenv('DISCORD_TOKEN')

handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

squeaks_strings = ["Squeak!", " -# Squeak", "squeak", "squeak!", "SQUEAK!", "SQUEAK", "Squeak"]

class User():
    def __init__(self, name: str, squeaks: int):
        self.name = name
        self.squeaks = squeaks
    
    def addSqueaks(self, amount: int):
        self.squeaks += amount

user_data = dict()

class Trap():
    def __init__(self, trap_user: str, cost: int = 5):
        self.trap_user = trap_user
        self.cost = cost
    def trigger(self, trapped_user: str):
        return f"{self.trap_user} has trapped {trapped_user} in a mouse trap! They lose {self.cost} squeaks!"

trap_array = []

def save_user_data(filename="user_data.txt"):
    with open(filename, "w", encoding="utf-8") as f:
        for user_id, user in user_data.items():
            f.write(f"{user_id},{user.name},{user.squeaks}\n")

def load_user_data(filename="user_data.txt"):
    if not os.path.exists(filename):
        return
    with open(filename, "r", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split(",")
            if len(parts) == 3:
                user_id, name, squeaks = parts
                user_data[int(user_id)] = User(name, int(squeaks))


@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} - {bot.user.id}')
    print('------')
    load_user_data()

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    
    await bot.process_commands(message)

    if "squeak" == message.content.lower():
        await message.channel.send(random.choice(squeaks_strings))
        if message.author.id not in user_data:
            user_data[message.author.id] = User(message.author.name, 0)

        if len(trap_array) > 0:
            for trap in trap_array:
                if trap.trap_user != message.author.name:
                    await message.channel.send(trap.trigger(message.author.name))
                    user_data[message.author.id].addSqueaks(-trap.cost)
                    trap_array.remove(trap)
                    save_user_data()
                    return
        
        user_data[message.author.id].addSqueaks(1)
        save_user_data()

# !sqcount
@bot.command()
async def sqcount(ctx):
    if ctx.author.id not in user_data:
        user_data[ctx.author.id] = User(ctx.author.name, 0)
    await ctx.send(f'You have squeaked {user_data[ctx.author.id].squeaks} times!')

@bot.command()
async def settrap(ctx, num: int = 5):
    # if author has done nothing yet make a profile for them
    if ctx.author.id not in user_data:
        user_data[ctx.author.id] = User(ctx.author.name, 0)
    if num < 5:
        await ctx.send("You need to set a trap with at least 5 squeaks!")
        return
    if user_data[ctx.author.id].squeaks < num:
        await ctx.send(f"You need at least {num} squeaks to set a trap!")
        return
    if ctx.author.id in [trap.trap_user for trap in trap_array]:
        await ctx.send("You already have a trap set!")
        return
    user_data[ctx.author.id].addSqueaks(-num)
    trap = Trap(ctx.author.name, num)
    trap_array.append(trap)
    await ctx.message.delete()
    save_user_data()
    await ctx.send(f"{ctx.author.name} has set a mouse trap!")

@bot.command()
async def disarmtrap(ctx, num: int):
    #Disarm the trap at the top of the array if the number the user provided is equal to the cost of the trap - 2
    #The player must have enough squeaks to disarm the trap
    if num < 3:
        await ctx.send("You need to disarm a trap with at least 3 squeaks!")
        return
    if ctx.author.id not in user_data:
        user_data[ctx.author.id] = User(ctx.author.name, 0)
    if user_data[ctx.author.id].squeaks < num:
        await ctx.reply(f"You do not have as many squeaks as you specified.")
        return
    if len(trap_array) == 0:
        await ctx.send("There are no traps set!")
        return
    if num != trap_array[0].cost - 2:
        await ctx.send(f"Failed to disarm the trap! You need to provide the cost of the trap minus 2 ({trap_array[0].cost - 2}). You will still lose squeaks for this failed attempt.")
        user_data[ctx.author.id].addSqueaks(-num)
        save_user_data()
        return
    # get the first trap that is not set by the user
    trap = trap_array[0]
    if trap.trap_user == ctx.author.name:
        if len(trap_array) > 1:
            trap = trap_array[1]
        else:
            await ctx.send("You cannot disarm your own trap!")
            return
    user_data[ctx.author.id].addSqueaks(-num)
    save_user_data()
    await ctx.send(f"You have disarmed {trap.trap_user}'s trap! You lose {num} squeaks, but the trap is no longer active. You saved 1 squeak by disarming it early!")
    
        
@bot.command()
async def seetraps(ctx):
    if len(trap_array) == 0:
        await ctx.send("There are no traps set!")
        return
    trap_list = "\n".join([f"{trap.trap_user} has a trap set!" for trap in trap_array])
    await ctx.send(f"Current traps:\n{trap_list}")

webserver.keep_alive()
bot.run(token, log_handler=handler, log_level=logging.DEBUG)