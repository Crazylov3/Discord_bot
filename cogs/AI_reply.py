import discord
from discord.ext import commands
import os


class AI_reply(commands.Cog):
    def __init__(self,client):
        self.client = client

def setup(client):
    client.add_cog(AI_reply(client))


