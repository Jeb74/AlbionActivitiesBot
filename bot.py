from __future__ import annotations

import asyncio
import json
import typing
from asyncio import sleep
from datetime import datetime, timedelta

import discord
import pytz
from discord import app_commands
from discord.app_commands import CheckFailure
from discord.ext import commands
import os
from dotenv import load_dotenv

from activity import Activity
from activityview import ActivityView
from splits import MenuView

DIFFERENCE = {
    "now": timedelta(seconds=10),
    "20m": timedelta(minutes=20),
    "1h": timedelta(hours=1),
    "2h": timedelta(hours=2),
    "3h": timedelta(hours=3),
    "4h": timedelta(hours=4),
    "5h": timedelta(hours=5),
    "6h": timedelta(hours=6),
    "7h": timedelta(hours=7),
    "8h": timedelta(hours=8),
    "1d": timedelta(days=1)
}


class AABot(discord.ext.commands.Bot):

    def __init__(self):
        load_dotenv(".env")
        self.___token = str(os.getenv("DISCORD_TOKEN"))
        intents = discord.Intents.all()
        intents.message_content = True
        self.___restricted_channels: dict[str:list[int]] = {}
        self.___split_channels: dict[str:tuple[int, int]] = {}
        super().__init__(command_prefix='/', intents=intents)
        for i in [i for i in dir(self) if i.startswith("_oninit_")]:
            getattr(self, i)()

    #######################################################################
    #            EVENTS
    #######################################################################

    async def on_ready(self):
        print("Albion Activities is ready!")
        try:
            synced = await self.tree.sync()
            print(f"Everything synced correctly! {len(synced)} command(s)")
        except Exception as e:
            print(e)
        with open("restrictions.json", mode="r") as f, open("ssc.json", mode="r") as f2:
            try:
                self.___restricted_channels = json.loads(f.read())
                self.___split_channels = json.loads(f2.read())
            except Exception as e:
                del e

    async def on_message(self, message: discord.Message):
        author_is_not_me = message.author.name != "Albion Activities"
        msg_is_not_cmd = len(message.content) > 0 and message.content[0] != "/"
        channel_is_not_allowed = False

        if not isinstance(message.channel, discord.DMChannel):
            guild = str(message.guild.id)
            if guild in self.___restricted_channels.keys():
                channel_is_not_allowed = message.channel.id in self.___restricted_channels.get(guild)
        if author_is_not_me and msg_is_not_cmd and channel_is_not_allowed:
            await message.delete()

    #######################################################################
    #            COMMANDS
    #######################################################################

    def _oninit_restrict(self):
        @self.tree.command(name="restrict", description="Restricts current channel. Reuse to remove restrictions.")
        @app_commands.check(self.is_guild_owner)
        async def restrict(interaction: discord.Interaction):
            try:
                guild = str(interaction.guild.id)
                id = interaction.channel.id
                if guild not in self.___restricted_channels.keys():
                    self.___restricted_channels[guild] = []
                cl: list[int] = self.___restricted_channels.get(guild)
                if id in cl:
                    cl.remove(id)
                    await interaction.response.send_message("This channel has been unrestricted.", ephemeral=True)
                else:
                    cl.append(id)
                    await interaction.response.send_message("This channel has been restricted.", ephemeral=True)
                with open("restrictions.json", mode="w") as f:
                    f.write(json.dumps(self.___restricted_channels))
            except Exception as e:
                del e

        @restrict.error
        async def restrict_error(interaction: discord.Interaction, error):
            if isinstance(error, CheckFailure):
                await interaction.response.send_message("You are not allowed to use this command!", ephemeral=True)
            else:
                await interaction.response.send_message(error, ephemeral=True)

    def _oninit_set_split_channel(self):
        @self.tree.command(name="ssc", description="Set splits' channel.")
        @app_commands.check(self.is_guild_owner)
        async def ssc(interaction: discord.Interaction):
            try:
                _id = interaction.channel.id
                self.___split_channels[str(interaction.guild.id)] = _id
                await interaction.response.send_message("This channel has been set for splits messages. Remember to restrict it.", ephemeral=True)
                with open("ssc.json", mode="w") as f:
                    f.write(json.dumps(self.___split_channels))
            except Exception as e:
                del e

        @ssc.error
        async def ssc_error(interaction: discord.Interaction, error):
            if isinstance(error, CheckFailure):
                await interaction.response.send_message("You are not allowed to use this command!", ephemeral=True)
            else:
                await interaction.response.send_message(error, ephemeral=True)

    def _oninit_restrictions(self):
        @self.tree.command(name="rl", description="Shows a list of all textual channels restricted.")
        async def restrictions(interaction: discord.Interaction):
            global ACTIVITY_COLOR
            message = "\n" + "\n".join([i.name for i in interaction.guild.channels if
                                        i.id in self.___restricted_channels.get(str(interaction.guild.id))])
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="Restricted Channels",
                    description=message
                ),
                ephemeral=True,
                delete_after=60
            )

    def _oninit_activity(self):
        @self.tree.command(name="activity", description="Create a new activity.")
        @app_commands.rename(wtd="activity", mnp="atleast_these_players", mxp="atmost_these_players")
        async def activity(
                interaction: discord.Interaction,
                wtd: typing.Literal["Ganking", "Fighting", "Hellgate"],
                mnp: int,
                mxp: int,
                start_after: typing.Literal["now", "20m", "1h", "2h", "3h", "4h", "5h", "6h", "7h", "8h", "1d"]):
            global RUNNING_ACTIVITIES
            global DIFFERENCE

            mnp = mnp if mnp > 1 else 2                                 # Min players calculation
            mxp = mxp if mxp >= mnp and mxp > 0 else 'unlimited'        # Max players calculation
            time_ = datetime.now(tz=pytz.timezone("Europe/Rome"))       # Getting current datetime
            status = [True]                                             # Setting current status for Activity enlisting
            difference = DIFFERENCE[start_after]                        # Setting activity starting time
            user_id: int = interaction.user.id                          # Getting user id
            guild_id: int = interaction.guild.id                        # Getting guild id
            ch_id: int = interaction.channel_id                         # Getting channel id

            a = Activity(user_id, wtd, mnp, mxp, time_, difference)
            await interaction.channel.send(embed=a.to_embed(), view=ActivityView(mnp, mxp, status, a))

            msg_id = interaction.guild.get_channel(interaction.channel.id).last_message.id                # Getting last message (this) id
            RUNNING_ACTIVITIES[msg_id] = a
            a.set_creation_msg(msg_id)

            asyncio.ensure_future(self.cct(guild_id, ch_id, start_after, status, a))
            await interaction.response.send_message("Activity created successfully.", ephemeral=True, delete_after=10)

    #######################################################################
    #            SUPPORT METHODS
    #######################################################################

    async def cct(self, g_id: int, c_id: int, start_at: str, active: list[bool], a: Activity): # create conditioned timeout
        global RUNNING_ACTIVITIES
        plustime = {
            "now": 10,
            "20m": 20 * 60,
            "1h": 60 * 60,
            "2h": 60 * 60 * 2,
            "3h": 60 * 60 * 3,
            "4h": 60 * 60 * 4,
            "5h": 60 * 60 * 5,
            "6h": 60 * 60 * 6,
            "7h": 60 * 60 * 7,
            "8h": 60 * 60 * 8,
            "1d": 60 * 60 * 24
        }[start_at]
        await sleep(plustime)
        if not a.reached_min():
            message = await self.get_guild(g_id).get_channel(c_id).fetch_message(a.get_creation_msg())
            await message.delete()
            RUNNING_ACTIVITIES.pop(a.get_creation_msg())
            del a
            return
        else:
            active[0] = False
        await self.create_split(g_id, a)

    async def create_split(self, g_id: int, a: Activity):
        a.get_creation_msg()
        split = self.___split_channels.get(str(g_id))                       # Getting information from split table
        ch = self.get_guild(g_id).get_channel(split)                        # Getting where to send the split and the number of splits
        await ch.send(embed=a.to_embed(), view=MenuView(a))
        a.set_split_msg(ch.last_message.id)

    async def is_guild_owner(self, interaction: discord.Interaction):
        return interaction.guild.owner_id == interaction.user.id

    def begin(self):
        super().run(self.___token)
