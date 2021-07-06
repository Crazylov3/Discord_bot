import discord
from discord.ext import commands
import numpy as np

class Basic_command(commands.Cog):
    def __init__(self,client):
        self.client = client

    @commands.command()
    async def girl(self,ctx):
        async with ctx.channel.typing():
            while True:
                try:
                    id = np.random.randint(0, 1378)
                    embed = discord.Embed(title="Gái ...🤤",colour=ctx.guild.me.colour)
                    embed.set_image(url = f"https://raw.githubusercontent.com/Crazylov3/Photo-Libary/main/Photos/{id}.png")
                    await ctx.send(embed = embed)
                    break
                except:
                    pass


def setup(client):
    client.add_cog(Basic_command(client))

