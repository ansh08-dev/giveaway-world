import discord
from discord.ext import commands
import asyncio
import json
import datetime
import os
from dotenv import load_dotenv
import random

# Load environment variables
load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")

# Bot Configuration
PREFIX = "g!"
SETTINGS_FILE = "settings.json"

bot = commands.Bot(command_prefix=PREFIX, intents=discord.Intents.all())

def load_settings():
    if not os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "w") as f:
            json.dump({"authorized_servers": [], "giveaways": []}, f)
    with open(SETTINGS_FILE, "r") as f:
        return json.load(f)

def save_settings(data):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(data, f, indent=4)

data = load_settings()

def is_authorized(guild_id):
    return guild_id in data["authorized_servers"]

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

# Authorization System
@bot.command()
async def authorize(ctx, server_id: int):
    if ctx.author.id != 1243885516466683944:  # Developer ID
        return await ctx.send("You are not authorized to use this command.")
    data["authorized_servers"].append(server_id)
    save_settings(data)
    await ctx.send(f"Server {server_id} has been authorized.")

@bot.command()
async def server(ctx):
    if ctx.author.id != 1243885516466683944:
        return await ctx.send("You are not authorized.")
    server_list = "\n".join([str(s) for s in data["authorized_servers"]])
    await ctx.send(f"Authorized Servers:\n{server_list}")

# Giveaway Hosting
@bot.command()
async def host(ctx, duration: int, winners: int, *, prize: str):
    if not is_authorized(ctx.guild.id):
        return await ctx.send("This server is not authorized to use Giveaway World.")
    
    embed = discord.Embed(title="🎉 Giveaway! 🎉", description=f"Prize: {prize}\nReact with 🎉 to enter!", color=discord.Color.gold())
    embed.add_field(name="Duration", value=f"{duration} minutes", inline=True)
    embed.add_field(name="Winners", value=winners, inline=True)
    embed.set_footer(text=f"Hosted by {ctx.author}")
    msg = await ctx.send(embed=embed)
    await msg.add_reaction("🎉")
    
    data["giveaways"].append({
        "message_id": msg.id,
        "channel_id": ctx.channel.id,
        "guild_id": ctx.guild.id,
        "prize": prize,
        "winners": winners,
        "end_time": (datetime.datetime.utcnow() + datetime.timedelta(minutes=duration)).isoformat()
    })
    save_settings(data)
    
    await asyncio.sleep(duration * 60)
    await end_giveaway(ctx.guild, msg.id)

async def end_giveaway(guild, message_id):
    giveaway = next((g for g in data["giveaways"] if g["message_id"] == message_id), None)
    if not giveaway:
        return
    
    channel = guild.get_channel(giveaway["channel_id"])
    msg = await channel.fetch_message(message_id)
    users = [user async for user in msg.reactions[0].users() if not user.bot]
    
    if len(users) < giveaway["winners"]:
        await channel.send("Not enough participants to select winners!")
    else:
        winners = random.sample(users, giveaway["winners"])
        await channel.send(f"🎉 Congratulations {', '.join(w.mention for w in winners)}! You won **{giveaway['prize']}**!")
    
    data["giveaways"] = [g for g in data["giveaways"] if g["message_id"] != message_id]
    save_settings(data)

@bot.command()
async def end(ctx, message_id: int):
    if not is_authorized(ctx.guild.id):
        return await ctx.send("This server is not authorized.")
    await end_giveaway(ctx.guild, message_id)

# Help Command
@bot.command()
async def ghelp(ctx):
    embed = discord.Embed(title="Giveaway World Help", color=discord.Color.blue())
    embed.add_field(name="g!host <duration> <winners> <prize>", value="Start a giveaway", inline=False)
    embed.add_field(name="g!end <message_id>", value="End a giveaway manually", inline=False)
    embed.add_field(name="g!authorize <server_id>", value="Authorize a server (Developer only)", inline=False)
    embed.add_field(name="g!server", value="Check authorized servers (Developer only)", inline=False)
    await ctx.send(embed=embed)

bot.run(TOKEN)
