import asyncio
from asyncio import sleep
from datetime import datetime

import discord.ui
import pytz
from discord import TextStyle
from discord.ui import TextInput

from activity import Activity
from activityview import RUNNING_ACTIVITIES  # noqa


class KickSelection(discord.ui.Select):
    def __init__(self, activity: Activity, guild: discord.Guild, split_msg: discord.Message):
        self.___activity = activity
        self.___split_msg = split_msg
        self.___once = False
        super().__init__(min_values=1, max_values=1, placeholder="Participants", options=[discord.SelectOption(label=guild.get_member(i[0]).display_name, value=i[0]) for i in activity.get_participants()]) # noqa

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer() # noqa
        if self.___once or self.___activity.get_min_players() == len(self.___activity.get_participants()):
            return
        value = self.values[0]
        if interaction.user.id == value:
            await interaction.user.send("You can't kick yourself!", delete_after=15)
            return
        self.___activity.remove_participant(value)
        self.___once = True
        await self.___split_msg.edit(embed=self.___activity.to_embed())
        await interaction.message.delete()


class KickView(discord.ui.View):
    def __init__(self, activity, guild, split_msg):
        super().__init__()
        self.add_item(KickSelection(activity, guild, split_msg))


class ClosingDialog(discord.ui.Modal):
    def __init__(self, channel_id: int, a: Activity):
        super().__init__(title="Last information")
        self.___channel_id = channel_id
        self.___a = a
        self.add_item(TextInput(label="Loot table name", style=TextStyle.short, row=0))
        self.add_item(TextInput(label="Total profit (without hypothetical taxes)", row=1))
        self.add_item(TextInput(label="Generic information", style=TextStyle.long, row=2, required=False))

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer() # noqa
        message: discord.Message = await interaction.guild.get_channel(self.___channel_id).fetch_message(self.___a.get_split_msg()) # noqa
        self.___a.set_loot_table(self.children[0].value) # noqa
        self.___a.set_profit(self.children[1].value) # noqa
        embed = self.___a.to_embed()
        val = self.children[2].value # noqa
        if val != "":
            embed = embed.add_field(name="Final comment", value=val, inline=False)
        await message.edit(embed=embed)


class GenericUtilsView(discord.ui.View):
    def __init__(self, activity: Activity):
        super().__init__(timeout=120)
        self.___a: Activity = activity

    @discord.ui.button(label="Register", style=discord.ButtonStyle.green)
    async def register(self, interaction: discord.Interaction, button:  discord.ui.Button): # noqa
        _id = interaction.user.id
        time_ = datetime.now(tz=pytz.timezone("Europe/Rome"))
        self.___a.add_participant(_id, time_)
        message = await interaction.channel.fetch_message(self.___a.get_split_msg())
        await message.edit(embed=self.___a.to_embed())
        await interaction.response.send_message("Operation ended successfully.", ephemeral=True, delete_after=15) # noqa

    @discord.ui.button(label="Kick", style=discord.ButtonStyle.red)
    async def kick(self, interaction: discord.Interaction, button: discord.ui.Button): # noqa
        await interaction.user.send(view=KickView(self.___a, interaction.guild, interaction.channel.fetch_message(self.___a.get_split_msg())), delete_after=20) # noqa

    @discord.ui.button(label="Close Activity", style=discord.ButtonStyle.green)
    async def close_activity(self, interaction: discord.Interaction, button: discord.ui.Button): # noqa
        self.___a.close()
        for i in interaction.guild.roles:
            if i.name == "Shotcaller":
                await interaction.guild.get_member(self.___a.get_shotcaller()).remove_roles(i)
        await interaction.response.send_modal(ClosingDialog(interaction.channel_id, self.___a))  # noqa


class VoteShotcallerSelection(discord.ui.Select):
    def __init__(self, activity: Activity, guild: discord.Guild, checks: list[bool, bool], votes: dict[int: list[int,int]]): # noqa
        self.___activity = activity
        self.___checks = checks
        self.___votes = votes
        super().__init__(min_values=1, max_values=1, placeholder="Select shotcaller", options=[discord.SelectOption(label=guild.get_member(i[0]).display_name, value=i[0]) for i in activity.get_participants()]) # noqa

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer() # noqa
        if self.___checks[0]:
            return
        value = int(self.values[0])
        self.___votes[value][0] += 1
        self.___checks[0] = True


class VoteSplitterSelection(discord.ui.Select):
    def __init__(self, activity: Activity, guild: discord.Guild, checks: list[bool, bool, discord.Message], votes: dict[int:list[int, int]]): # noqa
        self.___activity = activity
        self.___checks = checks
        self.___votes = votes
        super().__init__(min_values=1, max_values=1, placeholder="Select splitter", options=[discord.SelectOption(label=guild.get_member(i[0]).display_name, value=i[0]) for i in activity.get_participants()]) # noqa

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer() # noqa
        if self.___checks[1]:
            return
        value = int(self.values[0])
        self.___votes[value][1] += 1
        self.___checks[1] = True
        self.___checks[2] = interaction.message # noqa



class VoteView(discord.ui.View): # noqa
    def __init__(self, activity, guild, votes, routines: tuple[list[bool], int]):
        super().__init__(timeout=None)
        self.___checks: list[bool, bool] = [False, False, None]
        self.___routines = routines
        self.add_item(VoteShotcallerSelection(activity, guild, self.___checks, votes))
        self.add_item(VoteSplitterSelection(activity, guild, self.___checks, votes))
        asyncio.ensure_future(self.check_if_completed())

    async def check_if_completed(self):
        while not all(self.___checks[:2]):
            await sleep(5)
        self.___routines[0][self.___routines[1]] = True
        print(f"Routine {self.___routines[1]+1} ended successfully.")
        self.stop()
        await self.___checks[2].delete() # noqa


class MenuView(discord.ui.View):
    def __init__(self, a: Activity):
        super().__init__(timeout=None)
        self.___a: Activity = a
        self.___votes: dict[int, list[int]] = {}
        self.___already_started = self.___a.all_set()

    # Open Menu -> Register, Kick, Close Activity,
    @discord.ui.button(label="Open Menu", style=discord.ButtonStyle.gray)
    async def open_menu(self, interaction: discord.Interaction, button: discord.ui.Button): # noqa
        _id = interaction.user.id
        plrs = self.___a.get_participants()
        view = GenericUtilsView(self.___a)

        btn: discord.ui.Button = view.children[0]                  # noqa       # Register Button
        kick_btn: discord.ui.Button = view.children[1]             # noqa       # Kick Button
        close_btn: discord.ui.Button = view.children[2]            # noqa       # Close Button

        btn.disabled = _id in [i[0] for i in plrs] or self.___a.reached_max() or self.___a.is_closed()
        kick_btn.disabled = _id not in [self.___a.get_shotcaller(), self.___a.get_splitter()] or self.___a.is_closed()
        close_btn.disabled = _id != self.___a.get_splitter() or self.___a.is_closed()

        await interaction.response.send_message(view=view, ephemeral=True, delete_after=15)         # noqa

    @discord.ui.button(label="Vote", style=discord.ButtonStyle.red)
    async def vote(self, interaction: discord.Interaction, button: discord.ui.Button): # noqa
        if self.___a.all_set() or self.___already_started:
            await interaction.response.send_message("Poll already done. This button does nothing now.", delete_after=15, ephemeral=True) # noqa
            return
        if interaction.user.id not in [i[0] for i in self.___a.get_participants()]:
            await interaction.response.send_message("You are not enlisted in this activity. You cant start a Poll.", delete_after=15, ephemeral=True) # noqa
            return
        self.___already_started = True
        await interaction.response.defer() # noqa
        await interaction.channel.send("Poll started, check your private chat.", delete_after=30)

        routines: list[bool] = []                                                               # List of routines
        counter = 0                                                                             # Counter of coroutines
        for i in self.___a.get_participants():
            self.___votes[i[0]] = [0, 0]
            routines.append(False)
            view = VoteView(self.___a, interaction.guild, self.___votes, (routines, counter))
            counter += 1
            asyncio.ensure_future(self.create_poll(interaction.guild.get_member(i[0]), view))
            asyncio.ensure_future(self.results(routines, interaction.guild, interaction.channel_id))

    async def create_poll(self, member, view): # noqa
        await member.send(view=view)
    async def results(self, routines, guild, ch): # noqa
        while not all(routines):
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
