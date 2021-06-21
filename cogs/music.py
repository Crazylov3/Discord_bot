import discord
import re
import datetime as dt
from discord.ext import commands
from discord_slash.utils.manage_commands import create_choice, create_option
from discord_slash import cog_ext, SlashCommand, SlashContext
from discord import FFmpegPCMAudio
from youtube_dl import YoutubeDL
from enum import Enum
import random
import asyncio
import os
import typing as t
import DiscordUtils

URL_REGEX = r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))"
OPTIONS = {}
for i in range(1, 10):
    OPTIONS[f'{"1️⃣".replace("1", str(i))}'] = i-1

class AlreadyConnectedToChannel(commands.CommandError):
    pass


class NoVoiceChannel(commands.CommandError):
    pass


class QueueIsEmpty(commands.CommandError):
    pass


class PlayerIsAlreadyPaused(commands.CommandError):
    pass


class RepeatMode(Enum):
    NONE = 0
    ONE = 1
    ALL = 2


class Queue:
    def __init__(self):
        self._queue = []
        self.position = 0
        self.repeat_mode = RepeatMode.NONE

    @property
    def is_empty(self):
        return not self._queue

    @property
    def current_song(self):
        if not self._queue:
            raise QueueIsEmpty

        if self.position <= len(self._queue) - 1:
            return self._queue[self.position]

    @property
    def upcoming(self):
        if not self._queue:
            raise QueueIsEmpty

        return self._queue[self.position + 1:]

    @property
    def history(self):
        if not self._queue:
            raise QueueIsEmpty

        return self._queue[:self.position]

    @property
    def length(self):
        return len(self._queue)

    def add(self, *args):
        self._queue.extend(args)

    def get_next_song(self):
        if not self._queue:
            raise QueueIsEmpty
        if self.repeat_mode == RepeatMode.ONE:
            return self._queue[self.position]
        self.position += 1

        if self.position < 0:
            return None
        elif self.position > len(self._queue) - 1:
            if self.repeat_mode == RepeatMode.ALL:
                self.position = 0
            else:
                return None

        return self._queue[self.position]

    def shuffle(self):
        if not self._queue:
            raise QueueIsEmpty

        upcoming = self.upcoming
        random.shuffle(upcoming)
        self._queue = self._queue[:self.position + 1]
        self._queue.extend(upcoming)

    def set_repeat_mode(self, mode):
        if mode == "none":
            self.repeat_mode = RepeatMode.NONE
        elif mode == "Current Song":
            self.repeat_mode = RepeatMode.ONE
        elif mode == "Queue":
            self.repeat_mode = RepeatMode.ALL

    def clear_queue(self):
        self._queue.clear()
        self.position = 0


# noinspection PyTypeChecker
class Music(commands.Cog):
    FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
                      'options': '-vn'}

    def __init__(self, client):
        self.client = client
        self.queue = Queue()
        self.voice = None


    def play_next_song(self, ctx, voice):
        next_song = self.queue.get_next_song()
        if next_song is not None:
            source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(next_song['url'], **Music.FFMPEG_OPTIONS))
            voice.play(source, after=lambda e: self.play_next_song(ctx, voice))
            coro = ctx.send(
                embed=self.get_embed(ctx, self.queue._queue, [self.queue.position+1, self.queue.length]),
                delete_after=self.queue._queue[self.queue.position]['duration'])
            fut = asyncio.run_coroutine_threadsafe(coro, self.client.loop)
            try:
                fut.result()
            except:
                pass

    def get_embed(self, ctx, lis_song, state, type="Up Comming"):
        song = self.queue._queue[self.queue.position]
        embed = discord.Embed(title="Now Playing:",
                              description=f"🎶 {song['title'][:70]}" + \
                                          ("..." if len(song['title'][70:]) else "") + \
                                          f"`{song['duration'] // 60}:{song['duration'] % 60} `\n",
                              colour=ctx.author.colour)
        value = "."
        count = 0
        for index in range(state[0], state[1]):
            value += f"{index+1}.  {str(lis_song[index]['title'])[:70]}" + \
                     ("..." if len(lis_song[index]['title'][70:]) else "") + \
                     f"`{lis_song[index]['duration'] // 60}:{lis_song[index]['duration'] % 60}`\n"
            count += 1
            if count == 10:
                break
        embed.add_field(name=type, value=value,
                        inline=False)
        return embed

    async def choose_song(self, ctx, info):
        def _check(r, u):
            return (
                r.emoji in list(OPTIONS.keys())[:5]
                and u == ctx.author
                and r.message.id == msg.id
            )
        embed = discord.Embed(
            title="Which song do you want to play?",
            description="\n".join(f"{id+1}. {ent['title'][:80]}" + ("..." if len(ent['title'][80:]) else "") +
                                  f"{ent['duration'] // 60}:{ent['duration'] % 60}"
                                  for id, ent in enumerate(info["entries"])),
            colour=discord.colour.Colour.blue(),
            timestamp=dt.datetime.utcnow()
        )
        embed.set_footer(text=f"Invoked by {ctx.author.display_name}", icon_url=ctx.author.avatar_url)
        msg = await ctx.send(embed=embed)
        for name in list(OPTIONS.keys())[:5]:
            await msg.add_reaction(name)
        try:
            _reaction, _ = await self.client.wait_for("reaction_add", timeout=600.0,check=_check)
        except asyncio.TimeoutError:
            await msg.delete()
            await ctx.message.delete()
        else:
            await msg.delete()
            return info['entries'][OPTIONS[_reaction.emoji]]

    # @cog_ext.cog_slash(name="play", description="Play a song given by a url", options=[
    #     create_option(
    #         name="input",
    #         description="Url or name of song",
    #         option_type=3,
    #         required=True,
    #     )])
    @commands.command()
    async def play(self, ctx, *, input: t.Optional[str]):

        try:
            channel = ctx.guild.voice_channels[0]
            await channel.connect()
        except:
            pass
       # voice = discord.utils.get(self.client.voice_clients, guild=ctx.guild)
        self.voice = ctx.voice_client
        if re.match(URL_REGEX, input):
            YDL_OPTIONS = {'format': 'bestaudio'}
            with YoutubeDL(YDL_OPTIONS) as ydl:
                info = ydl.extract_info(input, download=False)
        else:
            YDL_OPTIONS = {'format': 'bestaudio', "ytsearch": "--default-search"}
            with YoutubeDL(YDL_OPTIONS) as ydl:
                _info = ydl.extract_info(f"ytsearch5:{input}", download=False)
                info = await self.choose_song(ctx, _info)
        if "entries" in info.keys():
            description = ""
            for id, ent in enumerate(info["entries"]):
                self.queue.add(ent)
                description += f"{id+1}.  {ent['title'][:70]}" + \
                               ("..." if len(ent['title'][70:]) else "") + \
                               f"`{ent['duration'] // 60}:{ent['duration'] % 60}`\n"
        else:
            self.queue.add(info)
            description = f"1. {info['title'][:70]}" + \
                          ("..." if len(info['title'][70:]) else "") + \
                          f"`{info['duration'] // 60}:{info['duration'] % 60}`\n"

        await ctx.channel.purge(limit=1)
        if not self.voice.is_playing():
            source = discord.PCMVolumeTransformer(
                discord.FFmpegPCMAudio(self.queue._queue[self.queue.position]['url'], **Music.FFMPEG_OPTIONS))
            self.voice.play(source, after=lambda e: self.play_next_song(ctx, self.voice))
            await ctx.send(embed=self.get_embed(ctx, self.queue._queue, [self.queue.position + 1, self.queue.length])
                           , delete_after=self.queue._queue[self.queue.position]['duration'])
        else:
            embed = discord.Embed(
                title="✅ | Added to queue",
                description=description,
                colour=ctx.author.colour,
                timestamp=dt.datetime.utcnow()
            )
            # embed.add_field(name="🎶",value="✅",inline=False)
            embed.set_footer(text=f"Invoked by {ctx.author.display_name}", icon_url=ctx.author.avatar_url)
            await ctx.send(embed=embed)

    @cog_ext.cog_slash(name="pause", description="Pause playing")
    async def pause(self, ctx):
        try:
            voice = discord.utils.get(self.client.voice_clients, guild=ctx.guild)
            voice.pause()

        except:
            pass
        finally:
            await ctx.send(embed=discord.Embed(
                title=" ⏸ | Paused"
            ))

    @cog_ext.cog_slash(name="resume", description="Resume playing")
    async def resume(self, ctx):
        try:
            self.voice.resume()
        except:
            pass
        finally:
            await ctx.send(embed=discord.Embed(
                title='▶ | Resumed'
            ))

    # @cog_ext.cog_slash(name="volume", description="Change the volume", options=[
    #     create_option(
    #         name="value",
    #         description="Percentage of volume",
    #         option_type=4,
    #         required=True
    #     )
    # ])
    @commands.command()
    async def volume(self, ctx, value: int):
        vol = max(0,value if value < 100 else 100)
        if self.voice.source.volume < value/100:
            await ctx.send(embed=discord.Embed(
                title=f'🔊 | {vol}%'
            ))
        else:
            await ctx.send(embed=discord.Embed(
                title=f'🔉 | {vol}%'
            ))
        self.voice.source.volume = vol/100

    @cog_ext.cog_slash(name="stop", description="Destroy the playing")
    async def stop(self, ctx):
        self.queue.clear_queue()
        self.voice.stop()
        await ctx.send(embed=discord.Embed(
            title='⏹ | Stopped.'
        ))

    @cog_ext.cog_slash(name="remove", description="remove a song from queue", options=[
        create_option(
            name="value",
            description="Percentage of volume",
            option_type=4,
            required=True
        )
    ])
    async def remove(self, ctx, value):
        title = self.queue._queue[value]['title']
        if self.queue.position > value:
            self.queue.position -= 1
        self.queue._queue.pop(value) if self.queue.position != value else ctx.send(
            embed=discord.Embed(title="This song is playing"))

        await ctx.send(embed=discord.Embed(
            title=f"✅ | Removed **  {title}  ** from the queue."
        ))

    @cog_ext.cog_slash(name="jump", description="jump into a song on the queue", options=[
        create_option(
            name="value",
            description="index of song",
            option_type=4,
            required=True
        )
    ])
    async def jump(self, ctx, value):
        self.queue.position = value-2
        self.voice.stop()
        await ctx.send(embed=self.get_embed(ctx, self.queue._queue, [(value), self.queue.length]))

    @cog_ext.cog_slash(name="shuffle", description="shuffle the queue")
    async def shuffle(self, ctx):
        print(self.queue.position)
        self.queue.shuffle()
        await ctx.send(embed=discord.Embed(title="🔀 | Shuffled the queue"))
        print(self.queue.position)

    @cog_ext.cog_slash(name="loop", description="jump into a song on the queue", options=[
        create_option(
            name="mode",
            description="index of song",
            option_type=3,
            required=True,
            choices=[
                create_choice(name="None", value="None"),
                create_choice(name="Current Song", value="Current Song"),
                create_choice(name="Queue", value="Queue")
            ]
        )
    ])
    async def loop(self, ctx, mode: str):
        self.queue.set_repeat_mode(mode)
        await ctx.send(embed=discord.Embed(title=f"🔂 | Loop mode set to {mode}"))

    @cog_ext.cog_slash(name="skip", description="skip current song")
    async def skip(self, ctx):
        self.voice.stop()
        if self.voice.is_playing():
            await ctx.send(embed=discord.Embed(title=f"⏭ | Skipped to {self.queue._queue[self.queue.position]['title']}"))
        else:
            await ctx.send(embed=discord.Embed(title="⏭ | Skipped"))

    @commands.command()
    async def queue(self, ctx):
        def _check(r, u):
            return (
                r.emoji in list(OPTIONS.keys())[:len(window_state)]
                and u == ctx.author
                and r.message.id == msg.id
            )
        if not self.queue._queue:
            await ctx.send(
                embed=discord.Embed(
                    title="Ops! The queue is empty!"
                )
            )
            return
        queue = self.queue._queue
        window_state = [(i * 10, i * 10 + 10) for i in range(len(queue) // 10)] + ([
            (len(queue) // 10 * 10, len(queue))]) if len(queue)%10!=0 else []
        old_state = 0
        msg = await ctx.send(embed=self.get_embed(ctx, queue, window_state[old_state],"Playlist :"), delete_after=600)
        await ctx.message.delete()

        while True:
            await msg.clear_reactions()
            for name in list(OPTIONS.keys())[:len(window_state)]:
                await msg.add_reaction(name)
            reaction, _ = await self.client.wait_for("reaction_add", timeout=600.0,check = _check)
            await msg.edit(embed=self.get_embed(ctx, queue, window_state[OPTIONS[reaction.emoji]], "Playlist :"))


def setup(client):
    client.add_cog(Music(client))
