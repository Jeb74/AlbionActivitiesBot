import asyncio
from asyncio import sleep
from datetime import datetime, timedelta
from discord.abc import AsyncIterator

import discord.ui
import pytz
from discord import TextStyle
from discord.ui import TextInput, Button

from activity import Activity


class KickSelection(discord.ui.Select):
    def __init__(self, activity: Activity, channel: discord.TextChannel):
        self.___activity = activity
        self.___channel = channel
        self.___once = False
        guild: discord.Guild = channel.guild
        super().__init__(min_values=1, max_values=1, placeholder="Participants", options=[discord.SelectOption(label=guild.get_member(i[0]).display_name, value=i[0]) for i in activity.get_participants()])

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        if self.___once or self.___activity.get_min_players() == len(self.___activity.get_participants()):
            print("Porco dio come mai?")
            return
        value = int(self.values[0])
        if interaction.user.id == value:
            await interaction.user.send("You can't kick yourself!", delete_after=15)
            return
        self.___activity.remove_participant(value)
        self.___once = True
        msg = await self.___channel.fetch_message(self.___activity.get_split_msg())
        await msg.edit(embed=self.___activity.to_embed())
        await interaction.message.delete()


class KickView(discord.ui.View):
    def __init__(self, activity, channel: discord.TextChannel):
        super().__init__()
        self.add_item(KickSelection(activity, channel))


class ClosingDialog(discord.ui.Modal):
    def __init__(self, channel_id: int, a: Activity):
        super().__init__(title="Last information")
        self.___channel_id = channel_id
        self.___a = a
        self.add_item(TextInput(label="Total profit (without hypothetical taxes)", row=0))
        self.add_item(TextInput(label="Generic information", style=TextStyle.long, row=1, required=False))

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        message: discord.Message = await interaction.guild.get_channel(self.___channel_id).fetch_message(self.___a.get_split_msg())
        self.___a.set_profit(self.children[0].value)
        embed = self.___a.to_embed()
        val = self.children[1].value
        if val != "":
            embed = embed.add_field(name="Final comment", value=val, inline=False)
        await message.edit(embed=embed)


class LockingDialog(discord.ui.Modal):
    def __init__(self, channel_id: int, a: Activity):
        super().__init__(title="Last information")
        self.___channel_id = channel_id
        self.___a = a
        self.add_item(TextInput(label="Loot table name", style=TextStyle.short, row=0))

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        message: discord.Message = await interaction.guild.get_channel(self.___channel_id).fetch_message(self.___a.get_split_msg())
        self.___a.set_loot_table(self.children[0].value)
        await message.edit(embed=self.___a.to_embed())


class GenericUtilsView(discord.ui.View):
    def __init__(self, activity: Activity, _id: int, top_menu):
        super().__init__(timeout=120)
        self.___a: Activity = activity
        self.___id = _id
        self.___top_menu = top_menu
        self._oninit_register()
        self._oninit_kick()
        self._oninit_lock()
        self._oninit_close()

    def _oninit_register(self):
        disabled = self.___id in [i[0] for i in self.___a.get_participants()] or self.___a.reached_max() or self.___a.is_closed()
        btn = Button(label="Register", style=discord.ButtonStyle.green, disabled=disabled)

        async def register(interaction: discord.Interaction):
            if self.___top_menu.is_locked():
                await interaction.response.send_message("This activity is locked, you can't join it anymore.", ephemeral=True, delete_after=15)
                return
            _id = interaction.user.id
            time_ = datetime.now(tz=pytz.timezone("Europe/Rome"))
            self.___a.add_participant(_id, time_)
            message = await interaction.channel.fetch_message(self.___a.get_split_msg())
            await message.edit(embed=self.___a.to_embed())
            await interaction.response.send_message("Operation ended successfully.", ephemeral=True, delete_after=15)

        btn.callback = register
        self.add_item(btn)

    def _oninit_kick(self):
        disabled = self.___id not in [self.___a.get_shotcaller(), self.___a.get_splitter()] or self.___a.is_closed()
        btn = Button(label="Kick", style=discord.ButtonStyle.red, disabled=disabled)

        async def kick(interaction: discord.Interaction):
            await interaction.user.send("Select a player to be kicked:", view=KickView(self.___a, interaction.channel), delete_after=20)

        btn.callback = kick
        self.add_item(btn)

    def _oninit_lock(self):
        disabled = self.___id != self.___a.get_splitter() or self.___a.is_closed()
        btn = Button(label="Lock", style=discord.ButtonStyle.red, disabled=disabled)

        async def lock(interaction: discord.Interaction):
            if not self.___a.is_closed():
                self.___top_menu.lock()
            await interaction.response.send_modal(LockingDialog(interaction.channel_id, self.___a))

        btn.callback = lock
        self.add_item(btn)

    def _oninit_close(self):
        disabled = self.___id != self.___a.get_splitter() or self.___a.is_closed()
        btn = Button(label="Close Activity", style=discord.ButtonStyle.green, disabled=disabled)

        async def close_activity(interaction: discord.Interaction):
            self.___a.close()
            for i in interaction.guild.roles:
                if i.name == "Shotcaller":
                    await interaction.guild.get_member(self.___a.get_shotcaller()).remove_roles(i)
            await interaction.response.send_modal(ClosingDialog(interaction.channel_id, self.___a))

        btn.callback = close_activity
        self.add_item(btn)


class VoteShotcallerSelection(discord.ui.Select):
    def __init__(self, activity: Activity, guild: discord.Guild, checks: list[bool, bool], votes: dict[int: list[int,int]]):
        self.___activity = activity
        self.___checks = checks
        self.___votes = votes
        super().__init__(min_values=1, max_values=1, placeholder="Select shotcaller", options=[discord.SelectOption(label=guild.get_member(i[0]).display_name, value=i[0]) for i in activity.get_participants()])

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        if self.___checks[0]:
            return
        value = int(self.values[0])
        self.___votes[value][0] += 1
        self.___checks[0] = True


class VoteSplitterSelection(discord.ui.Select):
    def __init__(self, activity: Activity, guild: discord.Guild, checks: list[bool, bool, discord.Message], votes: dict[int:list[int, int]]):
        self.___activity = activity
        self.___checks = checks
        self.___votes = votes
        super().__init__(min_values=1, max_values=1, placeholder="Select splitter", options=[discord.SelectOption(label=guild.get_member(i[0]).display_name, value=i[0]) for i in activity.get_participants()])

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        if self.___checks[1]:
            return
        value = int(self.values[0])
        self.___votes[value][1] += 1
        self.___checks[1] = True
        while not all(self.___checks):
            sleep(5)
        else:
            await interaction.message.delete()


class VoteView(discord.ui.View):
    def __init__(self, activity, guild, votes, routines: tuple[list[bool], int]):
        super().__init__(timeout=None)
        self.___checks: list[bool, bool] = [False, False]
        self.___routines = routines
        self.add_item(VoteShotcallerSelection(activity, guild, self.___checks, votes))
        self.add_item(VoteSplitterSelection(activity, guild, self.___checks, votes))
        asyncio.ensure_future(self.check_if_completed())

    async def check_if_completed(self):
        while not all(self.___checks[:2]):
            if self.___routines[0][self.___routines[1]]:
                self.stop()
                return
            await sleep(5)
        self.___routines[0][self.___routines[1]] = True
        self.stop()


class MenuView(discord.ui.View):
    def __init__(self, a: Activity):
        super().__init__(timeout=None)
        self.___a: Activity = a
        self.___votes: dict[int, list[int]] = {}
        self.___already_started = self.___a.all_set()
        self.___locked = False

    # Open Menu -> Register, Kick, Close Activity,
    @discord.ui.button(label="Open Menu", style=discord.ButtonStyle.gray)
    async def open_menu(self, interaction: discord.Interaction, button: discord.ui.Button):
        _id = interaction.user.id
        await interaction.response.send_message(view=GenericUtilsView(self.___a, _id, self), ephemeral=True, delete_after=15)

    @discord.ui.button(label="Vote", style=discord.ButtonStyle.red)
    async def vote(self, interaction: discord.Interaction, button: discord.ui.Button):
        if await self.vote_validations(interaction):
            return
        routines: list[bool] = []  # List of routines
        users: list[discord.Member] = []  # List of users
        for i in self.___a.get_participants():
            self.___votes[i[0]] = [0, 0]
            routines.append(False)
            users.append(interaction.guild.get_member(i[0]))
            view = VoteView(self.___a, interaction.guild, self.___votes, (routines, len(routines) - 1))
            asyncio.ensure_future(self.create_poll(users[-1], view))
        asyncio.ensure_future(self.results(routines, interaction.guild, interaction.channel_id, users))

    def lock(self):
        self.___locked = True

    def is_locked(self):
        return self.___locked

    async def create_poll(self, member, view):
        await member.send("Select which player should be shotcaller and which one should be splitter.", view=view)

    async def vote_validations(self, interaction: discord.Interaction):
        if self.___a.all_set() or self.___already_started:
            await interaction.response.send_message("Poll already done. This button does nothing now.", delete_after=15, ephemeral=True)
            return True
        if interaction.user.id not in [i[0] for i in self.___a.get_participants()]:
            await interaction.response.send_message("You are not enlisted in this activity. You cant start a Poll.", delete_after=15, ephemeral=True)
            return True
        self.___already_started = True
        await interaction.response.defer()
        await interaction.channel.send("Poll started, check your private chat.", delete_after=30)
        return False

    async def results(self, routines, guild, ch, users):
        end = datetime.now(pytz.timezone("Europe/Rome")) + timedelta(seconds=60)
        while not all(routines):
            if (end - datetime.now(pytz.timezone("Europe/Rome"))).total_seconds() <= 0:
                print("Ended without all completions.")
                for i in range(len(users)):
                    routines[i] = True
                    async for msg in users[i].dm_channel.history(oldest_first=False):
                        if msg is None:
                            break
                        await msg.delete()
                break
            await sleep(5)

        splitter_l = max([(i, self.___votes[i][1]) for i in self.___votes.keys()], key=lambda x: x[1])[0]
        shotcaller_l = max([(i, self.___votes[i][0]) for i in self.___votes.keys()], key=lambda x: x[1])[0]
        self.___a.set_splitter(splitter_l)
        self.___a.set_shotcaller(shotcaller_l)
        message: discord.Message = await guild.get_channel(ch).fetch_message(self.___a.get_split_msg())
        await message.edit(embed=self.___a.to_embed())
        try:
            for i in guild.roles:
                if i.name == "Shotcaller":
                    await guild.get_member(shotcaller_l).add_roles(i)
        except Exception as e:
            print(e.args)
