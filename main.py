import os
from dotenv import load_dotenv
import discord_slash
from discord_slash import SlashCommand, SlashContext
from discord_slash.utils.manage_commands import create_choice, create_option
import youtube_dl
import discord
from discord.ext import commands,tasks

load_dotenv()
client = commands.Bot(command_prefix="/")
slash = SlashCommand(client, sync_commands=True, sync_on_cog_reload=True)


@client.event
async def on_ready():
    await client.change_presence(status=discord.Status.online,activity=discord.Game("Cỏ"))

    print("Bot is ready")

@client.command()
async def ping(ctx):
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
