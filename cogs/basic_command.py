import discord
from discord.ext import commands
import numpy as np
from cogs.Google_API.init_photo_service import service

class Basic_command(commands.Cog):
    def __init__(self,client):
        self.client = client

    @commands.command()
    async def girl(self,ctx):
        async with ctx.channel.typing():
            with open("cogs/Google_API/Ids_file.txt", "r", encoding="utf-8") as file:
                arr = []
                for line in file:
                    arr.append(line)

            id = np.random.randint(0, len(arr))
            response = service.mediaItems().get(mediaItemId=arr[id].strip()).execute()
            embed = discord.Embed(title="Gái ...🤤")
            embed.set_image(url = response['baseUrl'])
            await ctx.send(embed = embed)


def setup(client):
    client.add_cog(Basic_command(client))

