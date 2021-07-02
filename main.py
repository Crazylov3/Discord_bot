import os
from dotenv import load_dotenv
from discord_slash import SlashCommand
import discord
from discord.ext import commands,tasks
import itertools

load_dotenv()
client = commands.Bot(command_prefix="/")
slash = SlashCommand(client, sync_commands=True, sync_on_cog_reload=True)
status = itertools.cycle(
    ["Meow ăn cơm", "Meow rửa bát", "Meow nghe nhạc", "Meow chơi đồ", "Meow tìm meow cái", "Crush từ chối Meow",
     "Tim Meow tan nát"
     "Meow bị buồn",
     "Meow bị mệt", "Meow muốn đi ngủ", "Meow đang ngủ","Meow tỉnh dậy và đang tìm đồ ăn" ,"Meow tập thể dục"])



@client.event
async def on_ready():
    for filename in os.listdir("cogs"):
        if filename.endswith(".py"):
            client.reload_extension(f"cogs.{filename[:-3]}")
    await client.change_presence(status=discord.Status.online,activity=discord.Game("Cỏ"))
    change_status.start()
    print("Bot is ready")
    
@tasks.loop(seconds=20)
async def change_status():
    await client.change_presence(status=discord.Status.online, activity=discord.CustomActivity(next(status)))

@client.command()
async def ping(ctx):
    print(ctx.guild.id)
    await ctx.reply(f"Ping: {round(client.latency*1000)} ms",mention_author=False)


@client.command()
async def unload(ctx, extension):
    try:
        client.unload_extension(f"cogs.{extension}")
    except:
        await ctx.channel.send(f"Can not find extension : {extension}")


@client.command()
async def load(ctx, extension):
    try:
        client.load_extension((f"cogs.{extension}"))
    except:
        await  ctx.channel.send(f"Can not find extension: {extension}")


for filename in os.listdir("cogs"):
    if filename.endswith(".py"):
        client.load_extension(f"cogs.{filename[:-3]}")

client.run(os.getenv("TOKEN"))
