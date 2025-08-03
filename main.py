import discord
from discord.ext import commands
import logging
from dotenv import load_dotenv
import os
import random
import webserver
import psycopg2
import time
from collections import defaultdict

# Track squeak timestamps per user
squeak_timestamps = defaultdict(list)

load_dotenv()
token = os.getenv('DISCORD_TOKEN')
DATABASE_URL = os.getenv('DATABASE_URL')
conn = psycopg2.connect(DATABASE_URL, sslmode='require')

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
        if self.squeaks < 0:
            self.squeaks = 0 # Prevent negative squeaks


user_data = dict()

class Trap():
    def __init__(self, trap_user: str, cost: int = 5, location_id: int = 0):
        self.trap_user = trap_user
        self.cost = cost
        self.location = location_id
    def trigger(self, trapped_user: str):
        return f"{self.trap_user} has trapped {trapped_user} in a mouse trap! They lose {self.cost} squeaks!"
    def verify_location(self, location_id: int):
        return self.location == location_id

trap_array = []

def init_db():
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY,
                name TEXT,
                squeaks INTEGER
            );
        """)
        conn.commit()

def save_user_data():
    with conn.cursor() as cur:
        for user_id, user in user_data.items():
            cur.execute("""
                INSERT INTO users (user_id, name, squeaks)
                VALUES (%s, %s, %s)
                ON CONFLICT (user_id)
                DO UPDATE SET name = EXCLUDED.name, squeaks = EXCLUDED.squeaks;
            """, (user_id, user.name, user.squeaks))
        conn.commit()


def load_user_data():
    with conn.cursor() as cur:
        cur.execute("SELECT user_id, name, squeaks FROM users;")
        for user_id, name, squeaks in cur.fetchall():
            user_data[user_id] = User(name, squeaks)




@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} - {bot.user.id}')
    print('------')
    init_db() # Initialize the database
    load_user_data()

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"Slow down! You can use this command again in {error.retry_after:.1f} seconds.")
    else:
        raise error  # re-raise other errors so you see them during development

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    
    if message.channel.name == "squeak-battles":
        await bot.process_commands(message)


    if "squeak" == message.content.lower():
        await message.channel.send(random.choice(squeaks_strings))

        if message.channel.name != "squeak-battles":
            return  # Only process squeaks in the squeak-battles channel
        if message.author.id not in user_data:
            user_data[message.author.id] = User(message.author.name, 0)

        # Check cooldown
        now = time.time()
        timestamps = squeak_timestamps[message.author.id]

        # Remove timestamps older than 60 seconds
        timestamps = [ts for ts in timestamps if now - ts < 60]
        squeak_timestamps[message.author.id] = timestamps

        if len(timestamps) >= 5:
            await message.channel.send("(No Points) You have already squeaked 5 times in the last 60 seconds!")
            return  # User already squeaked 5 times in the last 60 seconds — no points

        # Change this to be more luck based on if you trigger a trap
        for trap in trap_array:
            if trap.verify_location(message.channel.id) and trap.trap_user != message.author.name and random.randint(0, 100) < 30:  # 30% chance to trigger a trap
                await message.channel.send(trap.trigger(message.author.name))
                user_data[message.author.id].addSqueaks(-trap.cost)
                trap_array.remove(trap)
                save_user_data()
                return
        
        user_data[message.author.id].addSqueaks(1)
        squeak_timestamps[message.author.id].append(now)
        save_user_data()
    elif "gay" in message.content.lower() or "yuri" in message.content.lower():
        if message.channel.name in ["vent-here", "ranting"]: return  # Don't react in venting or ranting channels
        if random.randint(0, 100) < 10:  # 10% chance to gay react
            await message.add_reaction("🏳️‍🌈")
    elif "cheese" in message.content.lower():
        if message.channel.name in ["vent-here", "ranting"]: return
        if random.randint(0, 100) < 75:  # 50% chance to react with cheese
            return
        #reply to message
        await message.reply(random.choice(["*steals cheese*", "*eats cheese*", "gimme cheese?"]))

# !sqcount
@bot.command()
async def sqcount(ctx):
    if ctx.author.id not in user_data:
        user_data[ctx.author.id] = User(ctx.author.name, 0)
    await ctx.send(f'You have squeaked {user_data[ctx.author.id].squeaks} times!')

@bot.command()
@commands.cooldown(1, 60.0, commands.BucketType.channel)
async def sqleaderboard(ctx):
    if len(user_data) == 0:
        await ctx.send("No users have squeaked yet!")
        return
    # Sort and display the top 10 users by squeaks
    if ctx.author.id not in user_data:
        user_data[ctx.author.id] = User(ctx.author.name, 0)
    sorted_users = sorted(user_data.items(), key=lambda x: x[1].squeaks, reverse=True)
    leaderboard = "\n".join([f"{user[1].name}: {user[1].squeaks} squeaks" for user in sorted_users[:10]])
    await ctx.send(f"**Squeak Leaderboard:**\n{leaderboard}")

@bot.command()
@commands.cooldown(1, 60.0, commands.BucketType.user)
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
    user_data[ctx.author.id].addSqueaks(-num) # Deduct the cost of the trap from the user's squeaks
    trap = Trap(ctx.author.name, num, ctx.channel.id) # Create a trap and add it to the trap array
    trap_array.append(trap)
    await ctx.send(f"{ctx.author.name} has set a mouse trap!")
    #only delete if in a channel where the bot can delete messages
    if ctx.channel.permissions_for(ctx.guild.me).manage_messages:
        await ctx.message.delete() # Delete the user message
    save_user_data()

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
    # get the first trap that is not set by the user
    for trap in trap_array:
        if trap.trap_user == ctx.author.name:
            continue
        if trap.verify_location(ctx.channel.id):
            temptrap = trap
            break
    if temptrap is None:
        await ctx.send("No traps found in this channel that you can disarm!")
        return
    if num != temptrap.cost - 2:
        await ctx.send(f"Failed to disarm the trap! You need to provide the cost of the trap minus 2 ({temptrap.cost - 2}). You will still lose half of the squeaks you wagered.")
        user_data[ctx.author.id].addSqueaks(-num // 2)
        save_user_data()
        return
    if random.randint(0, 100) < 5:
        await ctx.send(f"You accidently set off the trap while attempting to disarm it! You lose all the squeaks you wagered and they go to {temptrap.trap_user}.")
        user_data[ctx.author.id].addSqueaks(-num)
        user_data[temptrap.trap_user].addSqueaks(num)
        trap_array.remove(temptrap)
        save_user_data()
        return
    save_user_data()
    await ctx.send(f"You successfully disarmed {temptrap.trap_user}'s trap! You keep the amount of squeaks you wagered.")
    trap_array.remove(temptrap)

        
@bot.command()
@commands.cooldown(1, 30.0, commands.BucketType.channel)
async def seetraps(ctx):
    if len(trap_array) == 0:
        await ctx.send("There are no traps set!")
        return
    trap_list = "\n".join([f"{trap.trap_user} has a trap set!" for trap in trap_array if trap.verify_location(ctx.channel.id)])
    if not trap_list:
        await ctx.send("There are no traps set in this channel!")
        return
    await ctx.send(f"Current traps:\n{trap_list}")

webserver.keep_alive()
bot.run(token, log_handler=handler, log_level=logging.DEBUG)