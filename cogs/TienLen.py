import asyncio
import numpy as np
import random
import re
import discord
from unidecode import unidecode
from discord.ext import commands
from discord_slash import cog_ext
from discord_slash.model import ButtonStyle
from discord_slash.utils.manage_commands import create_choice, create_option
from discord_slash.utils.manage_components import create_button, create_actionrow, wait_for_component, ComponentContext, \
    spread_to_rows
from cogs.GameAPI.create_board import create_current_board, create_user_board

list_card = []
mapping_point = {}
format = {}
number_cards = 13
for i in ['A'] + [f'{i}' for i in range(2, 11)] + ['J', 'Q', 'K']:
    list_card.extend([f"{i} ♧", f"{i} ♡", f"{i} ♤", f"{i} ♢"])
    format[f"{i} co"] = f"{i} ♡"
    format[f"{i} bich"] = f"{i} ♤"
    format[f"{i} ro"] = f"{i} ♢"
    format[f"{i} nhep"] = f"{i} ♧"
    if i.isdigit() and 3 <= int(i) <= 10:
        mapping_point[f"{i} ♧"] = float(i) + 0.2
        mapping_point[f"{i} ♡"] = float(i) + 0.4
        mapping_point[f"{i} ♢"] = float(i) + 0.3
        mapping_point[f"{i} ♤"] = float(i) + 0.1
    elif i == "A":
        mapping_point[f"{i} ♧"] = 14.2
        mapping_point[f"{i} ♡"] = 14.4
        mapping_point[f"{i} ♢"] = 14.3
        mapping_point[f"{i} ♤"] = 14.1
    elif i == "J":
        mapping_point[f"{i} ♧"] = 11.2
        mapping_point[f"{i} ♡"] = 11.4
        mapping_point[f"{i} ♢"] = 11.3
        mapping_point[f"{i} ♤"] = 11.1
    elif i == "Q":
        mapping_point[f"{i} ♧"] = 12.2
        mapping_point[f"{i} ♡"] = 12.4
        mapping_point[f"{i} ♢"] = 12.3
        mapping_point[f"{i} ♤"] = 12.1
    elif i == "K":
        mapping_point[f"{i} ♧"] = 13.2
        mapping_point[f"{i} ♡"] = 13.4
        mapping_point[f"{i} ♢"] = 13.3
        mapping_point[f"{i} ♤"] = 13.1
    else:
        mapping_point[f"{i} ♧"] = 15.2
        mapping_point[f"{i} ♡"] = 15.4
        mapping_point[f"{i} ♢"] = 15.3
        mapping_point[f"{i} ♤"] = 15.1



def _sort(arr):
    return sorted(arr, key=lambda x: (
        x.split(" ")[0] != "A", x.split(" ")[0] == "K", not x.split(" ")[0].isdigit(), x.split(" ")[0] == "10",
        x.split(" ")[0], x.split(" ")[1] != "♤", x.split(" ")[1] != "♧", x.split(" ")[1] != "♢",
        x.split(" ")[1] != "♡"))


class TienLen(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.guilds = [guild.id for guild in client.guilds]
        self._force_stop = {}
        self._lobby_status = {}
        self._playing_status = {}
        self._players_joined = {}
        self._number_player = {}
        self._msg_playing_player = {}
        self._player_cards = {}
        self._msg_main_playing = {}
        self._cycle_playing = {}
        self._origin_cycle_playing = {}
        self._total_number_moving = {}
        self._player_start_cycle = {}
        self._current_player = {}
        self._current_move = {}
        self._player_finished_playing = {}
        self._type_of_cycle = {}
        self._time_out = {}
        self._waiting_for_player_event = {}
        for guild_id in self.guilds:
            if guild_id not in self._playing_status.keys():
                self._playing_status[guild_id] = False
                self._lobby_status[guild_id] = False
                self._players_joined[guild_id] = []
                self._number_player[guild_id] = 0

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        if guild.id not in self._playing_status.keys():
            self._lobby_status[guild.id] = False
            self._playing_status[guild.id] = False
            self._players_joined[guild.id] = []
            self._number_player[guild.id] = 0
            self.guilds.append(guild.id)

    @staticmethod
    def _get_point(args):
        return sorted([mapping_point[arg] for arg in args])[-1]

    @staticmethod
    def _get_type(args):
        """
        return tuple : type of *args
        type (1,0): 1 lá, size = 1
        type (2,0): đôi, size =2
        type (3,0): bộ ba, size =3
        type (4,n): (dây, chiều dài của dây), size >= 3
        type (5,n): (tứ, số lượng tứ), size = 4*K
        type (6,n): (đôi thông, số lượng đôi thông), size 6+2*k
        """
        if args is None:
            return None
        points = sorted([int(mapping_point[arg]) for arg in args])
        if len(args) == 1:
            return 1, 0
        elif len(args) == 2 and points[0] == points[1]:
            return 2, 0
        elif len(args) == 3:
            if points[0] == points[1] == points[2]:
                return 3, 0
            elif points == list(range(min(points), max(points) + 1)) and points[-1] < 15:
                return 4, 3
        elif len(args) >= 4:
            unique, count = np.unique(points, return_counts=True)
            if len(points) % 4 == 0 and (count == 4).sum() == len(points) / 4:
                return 5, len(unique)
            elif points == list(range(min(points), max(points) + 1)) and points[-1] < 15:
                return 4, len(args)
            elif list(unique) == list(range(min(unique), max(unique) + 1)) and (count == 2).sum() == len(count):
                return 6, len(unique)
        return None
    def create_time_count(self,guild_id):
        count = 30
        while count:
            count -= 1
            if self._time_out[guild_id]:
                return
            time.sleep(1)
        coro_ = self._next_state(guild_id,skipped=self._cycle_playing[guild_id][0][self._current_player[guild_id]])
        fut_ = asyncio.run_coroutine_threadsafe(coro_, self.client.loop)

    def _create_cycle_playing(self, guild_id, initial_moving=None, player_start_cycle=None, type=0):
        self._current_move[guild_id] = initial_moving
        self._current_player[guild_id] = 0
        if self._total_number_moving[guild_id] == 0:
            arr = []
            for player in self._player_cards[guild_id].keys():
                points = sorted([mapping_point[arg] for arg in self._player_cards[guild_id][player]])
                arr.append((player, min(points)))
            cycle = [player[0] for player in sorted(arr, key=lambda x: x[1])]
            self._player_start_cycle[guild_id] = cycle[0]
            self._origin_cycle_playing[guild_id] = cycle.copy()
            self._cycle_playing[guild_id] = (cycle, type)
        elif player_start_cycle is None:
            print("Player start cycle is None")
            exit()
        else:
            self._player_start_cycle[guild_id] = player_start_cycle
            index = self._origin_cycle_playing[guild_id].index(player_start_cycle)
            self._cycle_playing[guild_id] = (self._origin_cycle_playing[guild_id][
                                             index:] + self._origin_cycle_playing[guild_id][:index], type)

    def _next_player(self, guild_id, skip=False):
        if skip:
            if self._current_player[guild_id] > len(self._cycle_playing[guild_id][0]) - 1:
                self._current_player[guild_id] = 0
        elif self._current_player[guild_id] < len(self._cycle_playing[guild_id][0]) - 1:
            self._current_player[guild_id] += 1
        elif self._current_player[guild_id] >= len(self._cycle_playing[guild_id][0]) - 1:
            self._current_player[guild_id] = 0

    def get_number_joined_player(self, guild_id):
        return len(self._players_joined[guild_id])

    def _check_valid_move(self, player_cards, old_move, new_move):
        if len(set(new_move)) != len(new_move):
            return False
        if not set(new_move).issubset(set(player_cards)):
            return False
        old_type = self._get_type(old_move)
        new_type = self._get_type(new_move)
        if old_type is None:
            return False if new_type is None else True

        if new_type is None:
            return False
        if old_type == new_type:
            return True if self._get_point(old_move) < self._get_point(new_move) else False
        elif new_type[0] == 5 and old_type[0] == 1 and int(mapping_point[old_move[0]]) == 15:
            return True
        elif new_type[0] == 6:
            if old_type[0] == 1 and int(mapping_point[old_move[0]]) == 15:
                return True
            elif new_type[1] == 4 and (
                    old_type[0] == 1 or old_type[0] == 2 or old_type == (5, 1) or old_type == (6, 3)):
                return True
        return False

    def _check_end_game(self, guild_id):
        """
        Case 1: type: (4,12)
        Case 2: type: (6,5)
        Case 3: tu quy 2
        Case 4: number of (2,0) = 6
        Case 5: number of (3,0) = 4
        Case 6: Out of card
        :return: Player or True if end else False
        """
        if self._force_stop.get(guild_id):
            return True
        if self._total_number_moving[guild_id] == 0:
            for player in self._player_cards[guild_id].keys():
                cards = self._player_cards[guild_id][player]
                points = np.array(sorted([int(mapping_point[arg]) for arg in cards]))
                unique, count = np.unique(points, return_counts=True)

                if len(unique) == 13 or (len(unique) == 12 and (unique == 15).sum() == 0):  # case 1
                    return player
                elif len(unique) >= 5:  # case 2
                    for j in range(0, len(unique) - 4):
                        if list(unique[j:j + 5]) == list(range(min(unique[j:j + 5]), max(unique[j:j + 5]) + 1)):
                            if (count[j:j + 5] >= 2).sum() == 5:
                                return player
                elif (points == 15).sum() == 4:  # case 3
                    return player
                elif (count >= 2).sum() == 6 or (count >= 3).sum() == 4:  # case 4
                    return player
        temp = 0
        for player in self._player_cards[guild_id].keys():
            if self._player_cards[guild_id][player]:
                temp += 1
            if temp >= 2:
                return False
        return True

    def _check_finished_player(self, guild_id, player):
        if not self._player_cards[guild_id][player]:
            self._player_finished_playing[guild_id].append(player)
            return player
        return False

    def _shuffle_cards(self, guild_id):
        random.shuffle(list_card)
        for j, player in enumerate(self._players_joined[guild_id]):
            self._player_cards[guild_id][player] = _sort(list_card[j * number_cards:(j + 1) * number_cards])

    async def _update_current_board(self, guild_id, new_move=None):
        if new_move is None:
            create_current_board(guild_id)
        else:
            create_current_board(guild_id, *new_move)

        guild = self.client.get_guild(856771318741205003)
        channel_target = discord.utils.find(lambda x: x.name == '2', guild.text_channels)
        msg = await channel_target.send(
            file=discord.File(f'cogs/GameAPI/playing_guild/{guild_id}/0current.png'))
        if self._player_finished_playing[guild_id]:
            description = "\n".join([f"**Rank {rank + 1}: {player.display_name}**" for rank, player in
                                     enumerate(self._player_finished_playing[guild_id])])
        else:
            description = "..."
        embed = discord.Embed(
            title=f"{self._cycle_playing[guild_id][0][self._current_player[guild_id]].display_name}'s turn",
            description=description)
        embed.set_image(url=msg.attachments[0].url)
        embed.set_footer(text="Use `/show_your_card` to see your card.")
        await self._msg_main_playing[guild_id].edit(content="The game has started", embed=embed)

    async def _next_state(self, guild_id, new_move=None, skipped=None, finished=None):      
        self._total_number_moving[guild_id] += 1
        self._time_out[guild_id] = True
        self._waiting_for_player_event[guild_id] = threading.Thread(target=self.create_time_count,
                                                                    args=[guild_id])
        if self._check_end_game(guild_id):
            self._playing_status[guild_id] = False
            self._lobby_status[guild_id] = False
            await self._msg_main_playing[guild_id].edit(
                embed=discord.Embed(title="Game Over",
                                    description="\n".join([f"Rank {k + 1}: {player.display_name}" for k, player in
                                                           enumerate(self._player_finished_playing[guild_id])]))
            )
        elif skipped:
            self._cycle_playing[guild_id][0].remove(skipped)
            if self._cycle_playing[guild_id][1] == 0:
                if len(self._cycle_playing[guild_id][0]) == 1:
                    self._create_cycle_playing(guild_id, player_start_cycle=self._cycle_playing[guild_id][0][0])
                else:
                    self._next_player(guild_id, skip=True)
            else:
                if len(self._cycle_playing[guild_id][0]) == 0:
                    self._create_cycle_playing(guild_id, player_start_cycle=self._player_start_cycle[guild_id])
                else:
                    self._next_player(guild_id, skip=True)
            await self._update_current_board(guild_id, self._current_move[guild_id])

        elif finished:
            index = self._origin_cycle_playing[guild_id].index(finished)
            if index >= len(self._origin_cycle_playing[guild_id]) - 1:
                player_start_cycle = self._origin_cycle_playing[guild_id][0]
            else:
                player_start_cycle = self._origin_cycle_playing[guild_id][index+1]

            self._origin_cycle_playing[guild_id].remove(finished)
            self._create_cycle_playing(guild_id, initial_moving=new_move, player_start_cycle=player_start_cycle, type=1)
            await self._update_current_board(guild_id, self._current_move[guild_id])

        else:
            if self._cycle_playing[guild_id][1] == 1:
                self._create_cycle_playing(guild_id, initial_moving=new_move,
                                           player_start_cycle=self._cycle_playing[guild_id][0][
                                               self._current_player[guild_id]])
                self._next_player(guild_id)
            else:
                self._current_move[guild_id] = new_move
                self._next_player(guild_id)
            await self._update_current_board(guild_id, self._current_move[guild_id])
            
        self._time_out[guild_id] = False
        time.sleep(1)
        self._waiting_for_player_event[guild_id].start()
        
    async def start_play(self, ctx):
        guild_id = ctx.guild.id
        self._playing_status[guild_id] = True
        self._origin_cycle_playing[guild_id] = []
        self._player_cards[guild_id] = {}
        self._total_number_moving[guild_id] = 0
        self._current_player[guild_id] = 0
        self._player_finished_playing[guild_id] = []
        self._shuffle_cards(guild_id)
        self._msg_main_playing[guild_id] = await ctx.channel.send(
            "Use `/show_your_card` to see your card.\n** The game will start in 5s **")
        await asyncio.sleep(5)
        self._create_cycle_playing(guild_id)
        player = self._check_end_game(guild_id)
        if isinstance(player, bool):
            await self._update_current_board(guild_id)
        else:
            self._playing_status[guild_id] = False
            self._lobby_status[guild_id] = False
            await self._msg_main_playing[guild_id].edit(
                embed=discord.Embed(title="Game Over",
                                    description=f"Rank 1: {player.display_name}")
            )

    async def _send_board_to_user(self, guild_id, player):
        user_name = player.display_name
        create_user_board(guild_id, user_name, *self._player_cards[guild_id][player])
        guild = self.client.get_guild(856771318741205003)
        channel_target = discord.utils.find(lambda x: x.name == '2', guild.text_channels)
        _msg = await channel_target.send(
            file=discord.File(f'cogs/GameAPI/playing_guild/{guild_id}/{user_name}.png'))
        embed = discord.Embed(title="Your cards:")
        embed.set_image(url=_msg.attachments[0].url)
        embed.set_footer(text="Choose cards you want to pick")
        cards = self._player_cards[guild_id][player]
        lis = [create_button(style=ButtonStyle.blue, label=f"{card}", custom_id=f"{card}") for card in cards]
        action_row = spread_to_rows(*lis) + [
            create_actionrow(create_button(style=ButtonStyle.gray, label="Send", custom_id="Send"),
                             create_button(style=ButtonStyle.red, label="Skip", custom_id="Skip"))]
        await self._msg_playing_player[guild_id][player].send(embed=embed, components=action_row, hidden=True)
        cards_picked = []
        while True:
            button_ctx: ComponentContext = await wait_for_component(self.client, components=action_row,
                                                                    check=lambda
                                                                        e: e.author == player and e.guild == player.guild)
            if self._check_end_game(guild_id):
                embed = discord.Embed(title="Game Over")
                action_row_ = create_actionrow(
                    create_button(style=ButtonStyle.red, label="Exit", custom_id="Exit", disabled=True))
                await button_ctx.edit_origin(content="Did you try your best?", embed=embed,
                                             components=[action_row_])
            elif player != self._cycle_playing[guild_id][0][self._current_player[guild_id]]:
                await button_ctx.edit_origin(content="Waiting for your turn, please!", embed=embed,
                                             components=action_row, hidden=True)
            elif button_ctx.custom_id == "Send":
                if self._check_valid_move(self._player_cards[guild_id][player],
                                          self._current_move[guild_id], cards_picked):
                    self._player_cards[guild_id][player] = [card for card in
                                                            self._player_cards[guild_id][player] if
                                                            card not in cards_picked]
                    temp = self._check_finished_player(guild_id, player)
                    if temp:
                        await self._next_state(guild_id, cards_picked, finished=player)

                        action_row_ = create_actionrow(
                            create_button(style=ButtonStyle.red, label="Exit", custom_id="Exit", disabled=True))
                        await button_ctx.edit_origin(
                            content=":sunglasses:",
                            embed=discord.Embed(
                                description=f"Your rank: {self._player_finished_playing[guild_id].index(player) + 1}"),
                            components=[action_row_]
                        )
                        break
                    else:
                        await self._next_state(guild_id, cards_picked)
                        create_user_board(guild_id, user_name, *self._player_cards[guild_id][player])
                        _msg = await channel_target.send(
                            file=discord.File(f'cogs/GameAPI/playing_guild/{guild_id}/{user_name}.png'))
                        embed.set_image(url=_msg.attachments[0].url)
                        embed.set_footer(text="Choose cards you want to pick")
                        cards = self._player_cards[guild_id][player]
                        lis = [create_button(style=ButtonStyle.blue, label=f"{card}", custom_id=f"{card}") for card
                               in
                               cards]

                        action_row = (spread_to_rows(*lis) if lis else []) + [
                            create_actionrow(create_button(style=ButtonStyle.gray, label="Send", custom_id="Send"),
                                             create_button(style=ButtonStyle.red, label="Skip", custom_id="Skip"))]
                        cards_picked = []
                        await button_ctx.edit_origin(content="You chose:", embed=embed, components=action_row,
                                                     hidden=True)

                else:
                    await button_ctx.edit_origin(
                        content="Invalid moving:\n" + ", ".join(f"{card}" for card in cards_picked), embed=embed,
                        components=action_row, hidden=True)
            elif button_ctx.custom_id == "Skip":
                if player not in self._cycle_playing[guild_id][0]:
                    await button_ctx.edit_origin(content="Skipped\n" + ", ".join(f"{card}" for card in cards_picked),
                                                 embed=embed,
                                                 components=action_row, hidden=True)
                else:
                    await self._next_state(guild_id, skipped=player)
                    await button_ctx.edit_origin(content="Skipped:\n" + ", ".join(f"{card}" for card in cards_picked),
                                                 embed=embed,
                                                 components=action_row,
                                                 hidden=True)

            else:
                if button_ctx.custom_id not in cards_picked:
                    cards_picked.append(button_ctx.custom_id)
                    await button_ctx.edit_origin(
                        content="You chose:\n" + ", ".join(f"{card}" for card in cards_picked), embed=embed,
                        components=action_row, hidden=True)
                else:
                    cards_picked.remove(button_ctx.custom_id)
                    await button_ctx.edit_origin(
                        content="You chose:\n" + ", ".join(f"{card}" for card in cards_picked), embed=embed,
                        components=action_row, hidden=True)

    @cog_ext.cog_slash(name="tienlen", description="Play a card game", options=[
        create_option(
            name="number",
            description="Number of player",
            option_type=4,
            required=True,
            choices=[
                create_choice(name="2", value=2),
                create_choice(name="3", value=3),
                create_choice(name="4", value=4)
            ]
        )
    ])
    async def tienlen(self, ctx, number):
        if self._lobby_status[ctx.guild.id]:
            await ctx.send(content="The lobby have already created", hidden=True)
        else:
            self._lobby_status[ctx.guild.id] = True
            self._players_joined[ctx.guild.id] = []
            self._number_player[ctx.guild.id] = int(number)
            self._players_joined[ctx.guild.id].append(ctx.author)
            description = '\n'.join(
                [f"*{author.display_name} joined*" for author in self._players_joined[ctx.guild.id]])
            embed = discord.Embed(
                title=f"Click `join` to join lobby and play card game with {ctx.author.display_name}",
                description=description,
                colour=ctx.guild.me.colour)
            embed.set_footer(
                text=f"Player : {len(self._players_joined[ctx.guild.id])}/{self._number_player[ctx.guild.id]}")
            action_row = create_actionrow(
                create_button(style=ButtonStyle.blue, label="Join", custom_id="Join"),
            )
            self._msg_main_playing[ctx.guild.id] = await ctx.send(embed=embed, components=[action_row])
            self._msg_playing_player[ctx.guild.id] = {}
            self._msg_playing_player[ctx.guild.id][ctx.author] = ctx
            while True:
                button_ctx: ComponentContext = await wait_for_component(self.client, components=[action_row],
                                                                        check=lambda e: e.guild == ctx.guild)
                if button_ctx.custom_id == "Start":
                    self._force_stop[ctx.guild.id] = False
                    await self._msg_main_playing[ctx.guild.id].delete()
                    await self.start_play(ctx)
                    break
                elif button_ctx.custom_id == "Join":
                    if button_ctx.author in self._players_joined[ctx.guild.id]:
                        await button_ctx.edit_origin(embed=embed)
                    else:
                        self._players_joined[ctx.guild.id].append(button_ctx.author)
                        if self.get_number_joined_player(ctx.guild.id) < self._number_player[ctx.guild.id]:
                            description = '\n'.join(
                                [f"*{author.display_name} joined*" for author in self._players_joined[ctx.guild.id]])
                            embed = discord.Embed(
                                title=f"Click `join` button to play card game with {button_ctx.author.display_name}",
                                description=description,
                                colour=ctx.guild.me.colour)
                            embed.set_footer(
                                text=f"Player : {len(self._players_joined[ctx.guild.id])}/{self._number_player[ctx.guild.id]}")
                        else:
                            description = '\n'.join(
                                [f"*{author.display_name} joined*" for author in self._players_joined[ctx.guild.id]])
                            embed = discord.Embed(
                                title=f"Click `Start` button to start the game",
                                description=description,
                                colour=ctx.guild.me.colour)
                            embed.set_footer(
                                text=f"Player : {len(self._players_joined[ctx.guild.id])}/{self._number_player[ctx.guild.id]}")
                            action_row = create_actionrow(
                                create_button(style=ButtonStyle.blue, label="Start", custom_id="Start"))
                            await button_ctx.edit_origin(embed=embed, components=[action_row])

    @cog_ext.cog_slash(name="show_my_card", description="Show your cards")
    async def show_my_card(self, ctx):
        await ctx.defer(hidden=True)
        if not self._playing_status[ctx.guild.id]:
            await ctx.send(content="The game haven't started")
        elif ctx.author not in self._players_joined[ctx.guild.id]:
            await ctx.send(content="You haven't joined the game yet!")
        else:
            self._msg_playing_player[ctx.guild.id][ctx.author] = ctx
            await self._send_board_to_user(ctx.guild.id, ctx.author)

    @commands.command(name="destroy_card_game")
    async def destroy_card_game(self, ctx):
        await ctx.message.delete()
        if not self._playing_status[ctx.guild.id]:
            await ctx.send(content="The game haven't started")
        elif ctx.author not in self._players_joined[ctx.guild.id]:
            await ctx.send(content="Only the participants of the game can cancel it!")
        else:
            self._force_stop[ctx.guild.id] = True
            self._lobby_status[ctx.guild.id] = False
            await self._msg_main_playing[ctx.guild.id].edit(
                embed=discord.Embed(description="Game Over")
            )
            self._playing_status[ctx.guild.id] = False


def setup(client):
    client.add_cog(TienLen(client))
