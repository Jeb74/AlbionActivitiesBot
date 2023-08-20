from __future__ import annotations

from datetime import datetime

import discord.ui
import pytz

from activity import Activity

RUNNING_ACTIVITIES: dict[int: Activity] = {}

class MenuView(discord.ui.View):
    def __init__(self, mmsg):
        super().__init__()
        self.mmsg_id = mmsg

    @discord.ui.button()
    async def register(self, interaction: discord.Interaction, button: discord.ui.Button):
        global RUNNING_ACTIVITIES
        a: Activity = RUNNING_ACTIVITIES.get(self.mmsg_id)
        if a.reached_max() and button.label == "Register":
            await interaction.response.send_message("Sorry, something went wrong.", ephemeral=True, delete_after=15)
            return
        time = datetime.now(tz=pytz.timezone("Europe/Rome"))
        if button.label == "Register":
            a.add_participant(interaction.user.id, time)
        elif button.label == "Unregister":
            a.remove_participant(interaction.user.id)
        await self.update_participants(a, interaction.channel_id, interaction.guild)
        await interaction.response.send_message("Operation ended successfully.", ephemeral=True, delete_after=15)

    async def update_participants(self, a: Activity, channel, guild):
        message: discord.Message = await guild.get_channel(channel).fetch_message(self.mmsg_id)
        embed = a.to_embed()
        await message.edit(embed=embed)


class ActivityView(discord.ui.View):
    def __init__(self, mnp: int, mxp: int | str, active: list[bool], activity: Activity):
        super().__init__(timeout=None)
        self.mnp: int = mnp
        self.mxp = mxp
        self.active = active
        self.___activity = activity

    @discord.ui.button(label="Open Menu", style=discord.ButtonStyle.gray)
    async def open_menu(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = await self.build_register_button(interaction)
        if not self.active[0]:
            btn = view.children[0]
            btn.disabled = True
        await interaction.response.send_message(view=view, ephemeral=True, delete_after=15)

#######################################################################
#            SUPPORT METHODS
#######################################################################

    async def build_register_button(self, interaction: discord.Interaction):
        global RUNNING_ACTIVITIES
        init_desc = interaction.message.embeds[0].fields[5].value.split("\n")
        view = MenuView(interaction.message.id)
        btn: discord.ui.Button = view.children[0]
        _id = interaction.user.id
        a: Activity = RUNNING_ACTIVITIES.get(interaction.message.id)
        participants = [i[0] for i in a.get_participants()]
        btn.label = "Unregister" if _id in participants else "Register"
        btn.style = discord.ButtonStyle.green if btn.label == "Register" else discord.ButtonStyle.red
        btn.disabled = a.reached_max() and _id not in participants
        return view

