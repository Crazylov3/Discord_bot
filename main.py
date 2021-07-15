import os
from dotenv import load_dotenv
from discord_slash import SlashCommand
import discord
from discord.ext import commands


load_dotenv()

client = commands.Bot(command_prefix=".",activity =discord.Activity(type=discord.ActivityType.listening, name="music"))
slash = SlashCommand(client, sync_commands=True, sync_on_cog_reload=True)


@client.event
async def on_ready():
    for filename in os.listdir("cogs"):
        if filename.endswith(".py"):
            client.reload_extension(f"cogs.{filename[:-3]}")

    print("Bot is ready")

@client.event
async def on_message(msg):
    if msg.channel.id == 865092377664028703 and msg.channel.name == "announce":
        if "Crazylov3:" in msg.content:
            ls = msg.content.split(":")
            title = ls[1]
            text = ls[2]
            for guild in client.guilds:
                general = discord.utils.find(lambda x: x.name.lower() == 'general' or x.name.lower() == 'chung', guild.text_channels)
                if general and general.permissions_for(guild.me).send_messages:
                    await general.send(embed=discord.Embed(title=title,description=text))
    else:
        await client.process_commands(msg)



@client.command()
async def ping(ctx):
    await ctx.reply(f"Ping: {round(client.latency * 1000)} ms", mention_author=False)




@client.command()
async def unload(ctx, extension):
    try:
        client.unload_extension(f"cogs.{extension}")
    except:
        await ctx.send(f"Can not find extension : {extension}")


@client.command()
async def load(ctx, extension):
    try:
        client.load_extension((f"cogs.{extension}"))
    except:
        await  ctx.send(f"Can not find extension: {extension}")


for filename in os.listdir("cogs"):
    if filename.endswith(".py"):
        client.load_extension(f"cogs.{filename[:-3]}")

client.run(os.getenv("TOKEN"))
