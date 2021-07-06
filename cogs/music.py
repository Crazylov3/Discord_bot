import asyncio
import datetime as dt
import os
import random
import re
from enum import Enum
import discord
from discord.ext import commands
from discord_slash import cog_ext
from discord_slash.model import ButtonStyle
from discord_slash.utils.manage_commands import create_choice, create_option
from discord_slash.utils.manage_components import create_button, create_actionrow, wait_for_component, ComponentContext
from youtube_dl import YoutubeDL

URL_REGEX = r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))"


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
    def __init__(self, args):
        self.list_guild_id = args
        self._queue = {}
        self.position = {}
        self.repeat_mode = {}

        for guild_id in self.list_guild_id:
            if guild_id not in self._queue.keys():
                self._queue[guild_id] = []
                self.position[guild_id] = 0
                self.repeat_mode[guild_id] = RepeatMode.NONE

    def is_empty(self, ID):
        return not self._queue[ID]

    def add_guild(self, *args):
        for guild in args:
            if guild.id not in self.list_guild_id:
                self.list_guild_id.append(guild.id)
                self._queue[guild.id] = []
                self.position[guild.id] = 0
                self.repeat_mode[guild.id] = RepeatMode.NONE

    def get_queue(self, ID):
        return self._queue[ID]

    def set_queue(self, ID, queue):
        self._queue[ID] = queue
        self.position[ID] = 0
        self.repeat_mode[ID] = RepeatMode.NONE

    def get_position(self, ID):
        return self.position[ID]

    def current_song(self, ID):
        if not self._queue[ID]:
            raise QueueIsEmpty

        if self.position[ID] <= len(self._queue[ID]) - 1:
            return self._queue[ID][self.position[ID]]

    def upcoming(self, ID):
        if not self._queue[ID]:
            raise QueueIsEmpty

        return self._queue[ID][self.position[ID] + 1:]

    def history(self, ID):
        if not self._queue[ID]:
            raise QueueIsEmpty

        return self._queue[ID][:self.position[ID]]

    def length(self, ID):
        return len(self._queue[ID])

    def add(self, ID, *args):
        self._queue[ID].extend(args)

    def get_next_song(self, ID):
        if not self._queue[ID]:
            return None
        if self.repeat_mode[ID] == RepeatMode.ONE:
            return self._queue[ID][self.position[ID]]
        self.position[ID] += 1

        if self.position[ID] < 0:
            return None
        elif self.position[ID] > len(self._queue[ID]) - 1:
            if self.repeat_mode[ID] == RepeatMode.ALL:
                self.position[ID] = 0
            else:
                return None

        return self._queue[ID][self.position[ID]]

    def shuffle(self, ID):
        if not self._queue[ID]:
            raise QueueIsEmpty

        upcoming = self.upcoming(ID)
        random.shuffle(upcoming)
        self._queue[ID] = self._queue[ID][:self.position[ID] + 1]
        self._queue[ID].extend(upcoming)

    def set_repeat_mode(self, ID, mode):
        if mode == "none":
            self.repeat_mode[ID] = RepeatMode.NONE
        elif mode == "Current Song":
            self.repeat_mode[ID] = RepeatMode.ONE
        elif mode == "Queue":
            self.repeat_mode[ID] = RepeatMode.ALL

    def clear_queue(self, ID):
        self._queue[ID].clear()
        self.position[ID] = 0


class Music(commands.Cog):
    FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
                      'options': '-vn'}

    def __init__(self, client):
        self.client = client
        self.queue = Queue([guild.id for guild in client.guilds])
        self.voice = {}  # list of voice client
        self._cache = {}  # msg need to delete
        self.channel_send_status = {}
        self.command_ctx = {}
        for guild_id in [guild.id for guild in client.guilds]:
            if guild_id not in self.voice.keys():
                self.voice[guild_id] = None
                self.channel_send_status[guild_id] = False

    @staticmethod
    async def check_status_bot_and_user(ctx):
        if ctx.guild.me.voice is None:
            await ctx.send(embed=discord.Embed(
                title="🚫 | The music haven't played yet!.",
                discription="Try to use command `/Play + url/name` to play music.",
                colour=discord.colour.Colour.red()
            ), hidden=True)
            return 0
        elif ctx.author.voice is None or ctx.guild.me.voice.channel != ctx.author.voice.channel:
            await ctx.send(embed=discord.Embed(
                title='🚫 | You must join the same voice channel with the bot!',
                colour=discord.colour.Colour.red()
            ), hidden=True)
            return 0
        return 1

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        general = discord.utils.find(lambda x: x.name == 'general', guild.text_channels)
        if general and general.permissions_for(guild.me).send_messages:
            await general.send(embed=discord.Embed(title="Hello everyone, I'm MeowMeow"))
        if guild.id not in self.voice.keys():
            self.voice[guild.id] = None
        self.queue.add_guild(guild)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.id == 854641854658510859:
            if after.channel is None:
                self.queue.clear_queue(member.guild.id)
                try:
                    self.voice[member.guild.id].stop()
                except:
                    pass
                self.voice[member.guild.id] = None
            elif before.channel is None:
                return
            elif after.channel.id != before.channel.id:
                self.queue.clear_queue(member.guild.id)
                try:
                    self.voice[member.guild.id].stop()
                except:
                    pass

    def get_content(self, ctx, lis_song, state, type="Up Comming"):
        song = self.queue.current_song(ctx.guild.id)
        if self.voice[ctx.guild.id].is_playing():
            content = "**Now Playing :**\n"
            content += f"```fix\n🎶 {self.queue.get_position(ctx.guild.id) + 1})" \
                       f" {song['title']} {song['duration'] // 60}:{song['duration'] % 60}\n```"

        else:
            content = "`/play + url` to play the song\n"
        if state[0] == state[1]:
            content += f"**{type}** : `Empty`"
        else:
            content += f"**{type}** :```css\n"
            count = 0
            for index in range(state[0], state[1]):
                content += f"{index + 1}) " + (
                    f"{str(lis_song[index]['title']):<65}" if len(
                        lis_song[index]['title']) < 60 else f"{str(lis_song[index]['title'])[:60] + '...':<65}") + \
                           f"{lis_song[index]['duration'] // 60}:{lis_song[index]['duration'] % 60}\n"

                count += 1
                if count == 10:
                    break
            content += f"\n      There are {len(self.queue.get_queue(ctx.guild.id)) - state[1]} more songs left." if len(
                self.queue.get_queue(ctx.guild.id)) > state[1] else "\n      This is end of the queue!"
            content += "\n```"

        return content

    async def choose_song(self, ctx, info):
        _text = "\n".join(f"{id + 1}) " + (f"{str(ent['title']):<65}" if len(ent['title']) < 60
                                           else f"{str(ent['title'])[:60] + '...':<65}") + \
                          f"{ent['duration'] // 60}:{ent['duration'] % 60}"
                          for id, ent in enumerate(info["entries"]))
        content = "Which song do you want to play?\n```css\n" + _text + "\n```"
        action_row = create_actionrow(
            create_button(style=ButtonStyle.blue, label="1"),
            create_button(style=ButtonStyle.blue, label="2"),
            create_button(style=ButtonStyle.blue, label="3"),
            create_button(style=ButtonStyle.blue, label="4"),
            create_button(style=ButtonStyle.blue, label="5"),
        )
        msg = await ctx.send(content=content, components=[action_row])
        try:
            button_ctx: ComponentContext = await wait_for_component(self.client, components=action_row)
        except:
            await msg.delete()
        else:
            await msg.delete()
            return info['entries'][int(button_ctx.component['label']) - 1]

    @cog_ext.cog_slash(name="connect", description="connect to author's voice channel")
    async def connect(self, ctx):
        if ctx.author.voice is None:
            await ctx.send(embed=discord.Embed(title="🚫 | You must join voice channel first"), hidden=True)
        else:
            await ctx.defer()
            try:
                channel = ctx.author.voice.channel
                await channel.connect()
                await ctx.send("Connected!")
            except:
                await ctx.send("Connected!")
            self.voice[ctx.guild.id] = ctx.guild.voice_client

    async def _connect(self, ctx):
        if ctx.author.voice is None:
            await ctx.send(embed=discord.Embed(title="🚫 | You must join voice channel first"), hidden=True)
            return 0
        else:
            try:
                channel = ctx.author.voice.channel
                await channel.connect()
            except:
                pass
            self.voice[ctx.guild.id] = ctx.guild.voice_client
            return 1

    @cog_ext.cog_slash(name="disconnect", description="disconnect from voice channel")
    async def disconnect(self, ctx):
        try:
            await ctx.defer()
            await self.voice[ctx.guild.id].disconnect()
            await ctx.send("Disconnected!")
        except:
            pass

    async def _play(self, ctx, channel_send=False):
        source = discord.PCMVolumeTransformer(
            discord.FFmpegPCMAudio(self.queue.current_song(ctx.guild.id)['url'], **Music.FFMPEG_OPTIONS))
        self.voice[ctx.guild.id].play(source, after=lambda e: self.play_next_song(ctx, self.voice[ctx.guild.id]))
        if not channel_send:
            self._cache[ctx.guild.id] = await ctx.send(self.get_content(ctx, self.queue.get_queue(ctx.guild.id),
                                                                        [self.queue.get_position(ctx.guild.id) + 1,
                                                                         min(self.queue.length(ctx.guild.id),
                                                                             self.queue.get_position(
                                                                                 ctx.guild.id) + 6)])
                                                       , delete_after=self.queue.current_song(ctx.guild.id)['duration'])
        else:
            self._cache[ctx.guild.id] = await ctx.channel.send(self.get_content(ctx, self.queue.get_queue(ctx.guild.id),
                                                                                [self.queue.get_position(
                                                                                    ctx.guild.id) + 1,
                                                                                 min(self.queue.length(ctx.guild.id),
                                                                                     self.queue.get_position(
                                                                                         ctx.guild.id) + 6)])
                                                               , delete_after=self.queue.current_song(ctx.guild.id)[
                    'duration'])

    def play_next_song(self, ctx, voice):
        next_song = self.queue.get_next_song(ctx.guild.id)
        if next_song is not None:
            try:
                if ctx.guild.id in self._cache.keys():
                    try:
                        coro_ = self._cache[ctx.guild.id].delete()
                        fut_ = asyncio.run_coroutine_threadsafe(coro_, self.client.loop)
                    except:
                        pass
                source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(next_song['url'], **Music.FFMPEG_OPTIONS))
                voice.play(source, after=lambda e: self.play_next_song(ctx, voice))
                if not self.channel_send_status[ctx.guild.id]:
                    coro = ctx.channel.send(
                        content=self.get_content(ctx, self.queue.get_queue(ctx.guild.id),
                                                 [self.queue.get_position(ctx.guild.id) + 1,
                                                  min(self.queue.get_position(ctx.guild.id) + 6,
                                                      self.queue.length(ctx.guild.id))]),
                        delete_after=self.queue.current_song(ctx.guild.id)['duration'])
                else:
                    coro = self.command_ctx[ctx.guild.id].send(
                        content=self.get_content(ctx, self.queue.get_queue(ctx.guild.id),
                                                 [self.queue.get_position(ctx.guild.id) + 1,
                                                  min(self.queue.get_position(ctx.guild.id) + 6,
                                                      self.queue.length(ctx.guild.id))]),
                        delete_after=self.queue.current_song(ctx.guild.id)['duration'])
                    self.channel_send_status[ctx.guild.id] = False

                fut = asyncio.run_coroutine_threadsafe(coro, self.client.loop)
                self._cache[ctx.guild.id] = fut.result()
            except:
                self.queue.get_queue(ctx.guild.id).pop(self.queue.get_position(ctx.guild.id))
                self.queue.position[ctx.guild.id] -= 1
                if self.queue.is_empty(ctx.guild.id):
                    return
                self.play_next_song(ctx, voice)

    @cog_ext.cog_slash(name="play", description="Play a song given by a url", options=[
        create_option(
            name="input",
            description="Url or name of song",
            option_type=3,
            required=True,
        )])
    async def play(self, ctx, input):
        choose_song = False

        if not await self._connect(ctx):
            return
        await ctx.defer()
        if re.match(URL_REGEX, input):
            YDL_OPTIONS = {'format': 'bestaudio',
                           'verbose': True, "quiet": True, "geo-bypass": True
                           }
            with YoutubeDL(YDL_OPTIONS) as ydl:
                info = ydl.extract_info(input, download=False)

        else:
            YDL_OPTIONS = {'format': 'bestaudio', "ytsearch": "--default-search",
                           'verbose': True, "quiet": True, "geo-bypass": True
                           }
            with YoutubeDL(YDL_OPTIONS) as ydl:
                _info = ydl.extract_info(f"ytsearch5:{input}", download=False)
                choose_song = True
                info = await self.choose_song(ctx, _info)
        if "entries" in info.keys():
            description = ""
            for id, ent in enumerate(info["entries"]):
                self.queue.add(ctx.guild.id, ent)
                description += f"{id + 1}.  {ent['title'][:70]}" + \
                               ("..." if len(ent['title'][70:]) else "") + \
                               f"`{ent['duration'] // 60}:{ent['duration'] % 60}`\n"
        else:
            self.queue.add(ctx.guild.id, info)
            description = f"1. {info['title'][:70]}" + \
                          ("..." if len(info['title'][70:]) else "") + \
                          f"`{info['duration'] // 60}:{info['duration'] % 60}`\n"

        if not self.voice[ctx.guild.id].is_playing():
            if not choose_song:
                await self._play(ctx, channel_send=False)
            else:
                await self._play(ctx, channel_send=True)

        else:
            embed = discord.Embed(
                title="✅ | Added to queue",
                description=description,
                colour=ctx.guild.me.colour,
                timestamp=dt.datetime.utcnow()
            )
            embed.set_footer(text=f"Invoked by {ctx.author.display_name}", icon_url=ctx.author.avatar_url)
            if not choose_song:
                await ctx.send(embed=embed, delete_after=120)
            else:
                await ctx.channel.send(embed=embed, delete_after=120)

    @cog_ext.cog_slash(name="pause", description="Pause playing")
    async def pause(self, ctx):
        if await Music.check_status_bot_and_user(ctx):
            self.voice[ctx.guild.id].pause()
            await ctx.send(embed=discord.Embed(
                title=" ⏸ | Paused",
                colour=ctx.guild.me.colour
            ), delete_after=60)

    @cog_ext.cog_slash(name="resume", description="Resume playing")
    async def resume(self, ctx):
        if await Music.check_status_bot_and_user(ctx):
            self.voice[ctx.guild.id].resume()
            await ctx.send(embed=discord.Embed(
                title='▶ | Resumed',
                colour=ctx.guild.me.colour
            ), delete_after=60)

    @cog_ext.cog_slash(name="volume", description="Change the volume", options=[
        create_option(
            name="value",
            description="Percentage of volume",
            option_type=4,
            required=True
        )
    ])
    async def volume(self, ctx, value: int):
        if await Music.check_status_bot_and_user(ctx):
            vol = max(0, value if value < 100 else 100)
            if self.voice[ctx.guild.id].source.volume < value / 100:
                await ctx.send(embed=discord.Embed(
                    title=f'🔊 | {vol}%',
                    colour=ctx.guild.me.colour
                ), delete_after=60)
            else:
                await ctx.send(embed=discord.Embed(
                    title=f'🔉 | {vol}%',
                    colour=ctx.guild.me.colour
                ), delete_after=60)
            self.voice[ctx.guild.id].source.volume = vol / 100

    @cog_ext.cog_slash(name="stop", description="Destroy the playing")
    async def stop(self, ctx):
        if await Music.check_status_bot_and_user(ctx):
            if self.voice[ctx.guild.id].is_playing():
                await ctx.defer(hidden=False)
                self.queue.clear_queue(ctx.guild.id)
                self.voice[ctx.guild.id].stop()
                await ctx.send(embed=discord.Embed(
                    title='⏹ | Stopped.',
                    colour=ctx.guild.me.colour
                ), delete_after=60)
            else:
                await ctx.send(embed=discord.Embed(
                    title="⏹ | The music haven't played yet!",
                    colour=discord.colour.Colour.red()
                ), hidden=True)

    @cog_ext.cog_slash(name="remove", description="remove a song from queue", options=[
        create_option(
            name="value",
            description="Index of song you want to remove",
            option_type=4,
            required=True
        )
    ])
    async def remove(self, ctx, value):
        if await Music.check_status_bot_and_user(ctx):
            if 0 < value <= self.queue.length(ctx.guild.id) and self.queue.get_position(ctx.guild.id) != (
                    value - 1):
                await ctx.defer(hidden=False)
                title = self.queue.get_queue(ctx.guild.id)[value - 1]["title"]
                if self.queue.get_position(ctx.guild.id) > (value - 1):
                    self.queue.position[ctx.guild.id] -= 1
                self.queue.get_queue(ctx.guild.id).pop(value - 1)
                await ctx.send(embed=discord.Embed(
                    title=f"✅ | Removed {title}  from the queue.",
                    colour=ctx.guild.me.colour
                ), delete_after=60)
                return
            elif self.queue.get_position(ctx.guild.id) == (value - 1):
                await ctx.send(embed=discord.Embed(
                    title='🚫 | This song is playing.',
                    colour=discord.colour.Colour.red()
                ), hidden=True)
                return
            else:
                await ctx.send(embed=discord.Embed(
                    title='🚫 | Invalid index.',
                    colour=discord.colour.Colour.red()
                ), hidden=True)

    @cog_ext.cog_slash(name="jump", description="jump into a song on the queue", options=[
        create_option(
            name="value",
            description="index of song",
            option_type=4,
            required=True
        )
    ])
    async def jump(self, ctx, value):

        if await Music.check_status_bot_and_user(ctx):
            if 0 < value <= self.queue.length(ctx.guild.id):
                await ctx.defer()
                if self.voice[ctx.guild.id].is_playing():
                    self.command_ctx[ctx.guild.id] = ctx
                    self.channel_send_status[ctx.guild.id] = True
                    self.queue.position[ctx.guild.id] = value - 2
                    self.voice[ctx.guild.id].stop()
                else:
                    self.queue.position[ctx.guild.id] = value - 1
                    await self._play(ctx, channel_send=False)

            else:
                await ctx.send(embed=discord.Embed(
                    title='🚫 | Invalid index.',
                    colour=discord.colour.Colour.red()
                ), hidden=True)

    @cog_ext.cog_slash(name="shuffle", description="shuffle the queue")
    async def shuffle(self, ctx):
        if await Music.check_status_bot_and_user(ctx):
            self.queue.shuffle(ctx.guild.id)
            await ctx.send(embed=discord.Embed(title="🔀 | Shuffled the queue", colour=ctx.guild.me.colour),
                           delete_after=60)

    @cog_ext.cog_slash(name="loop", description="set loop option", options=[
        create_option(
            name="mode",
            description="loop options",
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
        if await Music.check_status_bot_and_user(ctx):
            self.queue.set_repeat_mode(ctx.guild.id, mode)
            await ctx.send(embed=discord.Embed(title=f"🔂 | Loop mode set to {mode}", colour=ctx.guild.me.colour),
                           delete_after=60)

    @cog_ext.cog_slash(name="skip", description="skip current song")
    async def skip(self, ctx):

        if await Music.check_status_bot_and_user(ctx):
            if self.voice[ctx.guild.id].is_playing():
                self.command_ctx[ctx.guild.id] = ctx
                self.channel_send_status[ctx.guild.id] = True
                await ctx.defer()
                self.voice[ctx.guild.id].stop()

            else:
                await ctx.send(
                    embed=discord.Embed(title="🚫 | The music haven't played yet!", colour=discord.colour.Colour.red()),
                    hidden=True)

    @cog_ext.cog_slash(name="playlist", description="Show the queue")
    async def playlist(self, ctx):
        if await Music.check_status_bot_and_user(ctx):
            await ctx.defer()
            if not self.queue.get_queue(ctx.guild.id):
                await ctx.send(
                    embed=discord.Embed(
                        title="Ops! The queue is empty!"
                    ),
                    hidden=True
                )
                return
            window_state = [(i * 10, i * 10 + 10) for i in range(len(self.queue.get_queue(ctx.guild.id)) // 10)] + \
                           ([(len(self.queue.get_queue(ctx.guild.id)) // 10 * 10,
                              len(self.queue.get_queue(ctx.guild.id)))] if len(
                               self.queue.get_queue(ctx.guild.id)) % 10 != 0 else [])
            current_state = 0
            action_row = create_actionrow(
                create_button(style=ButtonStyle.blue, label="First"),
                create_button(style=ButtonStyle.blue, label="Back"),
                create_button(style=ButtonStyle.blue, label="Next"),
                create_button(style=ButtonStyle.blue, label="Last"),
            )
            await ctx.send(
                content=self.get_content(ctx, self.queue.get_queue(ctx.guild.id), window_state[current_state],
                                         "Playlist"),
                components=[action_row],
                delete_after=600
            )
            while True:
                window_state_cache = [(i * 10, i * 10 + 10) for i in
                                      range(len(self.queue.get_queue(ctx.guild.id)) // 10)] + \
                                     ([(len(self.queue.get_queue(ctx.guild.id)) // 10 * 10,
                                        len(self.queue.get_queue(ctx.guild.id)))] if len(
                                         self.queue.get_queue(ctx.guild.id)) % 10 != 0 else [])
                button_ctx: ComponentContext = await wait_for_component(self.client, components=action_row)
                if window_state_cache == window_state:
                    current_state = update_state(current_state, button_ctx.component['label'], len(window_state))
                else:
                    window_state = window_state_cache
                    current_state = 0
                await button_ctx.edit_origin(
                    content=self.get_content(ctx, self.queue.get_queue(ctx.guild.id), window_state[current_state],
                                             "Playlist"),
                    components=[action_row],
                    delete_after=600
                )

    @cog_ext.cog_slash(
        name="savequeue",
        description="save the current queue",
        options=[
            create_option(
                name="name",
                description="Name the playlist you want to save",
                option_type=3,
                required=True
            )
        ]
    )
    async def savequeue(self, ctx, name: str):
        if await Music.check_status_bot_and_user(ctx):
            if not self.queue.is_empty(ctx.guild.id):
                dirName = f"list_queue/{ctx.guild.id}"
                txtName = f"list_queue/{ctx.guild.id}/{name.lower().strip()}.txt"
                info = {"Author": ctx.author.display_name, "Date created": dt.datetime.utcnow()}
                if not os.path.exists(dirName):
                    os.makedirs(dirName)
                if os.path.exists(txtName):
                    await ctx.send(embed=discord.Embed(
                        title="🚫 | This name has already been given, please choose another name!",
                        colour=discord.colour.Colour.red()
                    ), hidden=True)
                else:
                    await ctx.defer()
                    with open(txtName, "w+", encoding="utf-8") as file:
                        for key in ["Author", "Date created"]:
                            file.write(key + ":*:" + str(info[key]) + "\n")
                        for song in self.queue.get_queue(ctx.guild.id):
                            file.write(song["title"] + ":*:" + str(song["duration"]) + ":*:" + song["url"] + "\n")
                        file.close()
                    embed = discord.Embed(
                        title=f"Saved current queue: **{name.lower().strip()}**",
                        colour=ctx.guild.me.colour,
                        timestamp=dt.datetime.utcnow()
                    )
                    embed.set_footer(text=f"Invoked by {ctx.author.display_name}", icon_url=ctx.author.avatar_url)
                    await ctx.send(embed=embed, delete_after=120)
            else:
                await ctx.send(embed=discord.Embed(
                    title="🚫 | Queue is empty!"
                ), hidden=True)

    @cog_ext.cog_slash(
        name="loadqueue",
        description="Load the saved queue",
        options=[
            create_option(
                name="queuename",
                description="Name the queue",
                option_type=3,
                required=True
            )
        ]
    )
    async def loadqueue(self, ctx, queuename: str):
        if ctx.author.voice is None:
            await ctx.send(embed=discord.Embed(
                title='🚫 | You must join the voice channel to use this command!',
                colour=discord.colour.Colour.red()
            ), hidden=True)
            return
        txtName = f"list_queue/{ctx.guild.id}/{queuename.lower().strip()}.txt"
        if not os.path.exists(txtName):
            await ctx.send(embed=discord.Embed(
                title="🚫 | Invaild name of queue!",
                colour=discord.colour.Colour.red()
            ), hidden=True)
        else:
            await ctx.defer()
            await self._connect(ctx)
            queue = []
            info = {}
            with open(txtName, "r", encoding="utf-8") as file:
                for i, line in enumerate(file):
                    if i < 2:
                        info[line.rstrip().split(":*:")[0]] = line.rstrip().split(":*:")[1]
                    else:
                        song = line.rstrip().split(":*:")
                        queue.append({"title": song[0], "duration": int(song[1]), "url": song[2]})
            embed = discord.Embed(
                title=f"✅ | Successfully load the `{queuename.lower().strip()}`!",
                description=f"Playlist Author: `{info['Author']}`\nDate created: {info['Date created']}"
            )
            await ctx.send(embed=embed, delete_after=120)
            self.queue.set_queue(ctx.guild.id, queue)
            self.queue.position[ctx.guild.id] -= 1
            try:
                self.voice[ctx.guild.id].stop()
            except:
                pass

    @cog_ext.cog_slash(name="savedqueue", description="Show the list of saved queue")
    async def savedqueue(self, ctx):
        await ctx.defer()
        lis = []
        if os.path.exists(f"list_queue/{ctx.guild.id}"):
            for filename in os.listdir(f"list_queue/{ctx.guild.id}"):
                if filename.endswith(".txt"):
                    lis.append(filename[:-4])
            await ctx.send(embed=discord.Embed(
                title="List of saved queue: ",
                description="\n".join([f"+, {name}" for name in lis]),
                colour=ctx.guild.me.colour
            ))
        else:
            await ctx.send(embed=discord.Embed(
                title="You haven't saved any queue yet!",
                colour=discord.colour.Colour.red()
            ), hidden=True)


def update_state(current, command, limit):
    new = current
    if command == "First":
        new = 0
    elif command == "Back":
        new = max(0, current - 1)
    elif command == "Next":
        new = min(current + 1, limit - 1)
    elif command == "Last":
        new = limit - 1
    return new


def setup(client):
    client.add_cog(Music(client))
