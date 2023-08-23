from __future__ import annotations

from datetime import datetime

import discord.ui
import pytz
from discord.ui import Button

from activity import Activity
from data import RUNNING_ACTIVITIES


class MenuView(discord.ui.View):
    def __init__(self, activity, msg, user):
        super().__init__()
        self.msg_id = msg
        self.a: Activity = activity
        self.user = user
        self._oninit_register()

    def _oninit_register(self):
        registrable = self.user not in [i[0] for i in self.a.get_participants()]
        btn = Button(
            label="Register" if registrable else "Unregister",
            disabled=registrable and self.a.reached_max() or self.a.is_started(),
            style=discord.ButtonStyle.green if registrable else discord.ButtonStyle.red
        )

        async def register(interaction: discord.Interaction):
            if registrable and not self.a.reached_max():
                time = datetime.now(tz=pytz.timezone("Europe/Rome"))
                self.a.add_participant(self.user, time)
            elif not registrable:
                self.a.remove_participant(self.user)
            else:
                await interaction.response.send_message("This activity reached the maximum number of participants.", ephemeral=True, delete_after=15)
            message: discord.Message = await interaction.channel.fetch_message(self.msg_id)
            await message.edit(embed=self.a.to_embed())
            await interaction.response.send_message("Operation ended successfully.", ephemeral=True, delete_after=15)
        btn.callback = register
        self.add_item(btn)


class ActivityView(discord.ui.View):
    def __init__(self, activity: Activity):
        super().__init__(timeout=None)
        self.___a = activity

    @discord.ui.button(label="Open Menu", style=discord.ButtonStyle.gray)
    async def open_menu(self, interaction: discord.Interaction, button: discord.ui.Button):
        msg_id = interaction.message.id
        user_id = interaction.user.id
        await interaction.response.send_message(view=MenuView(self.___a, msg_id, user_id), ephemeral=True, delete_after=15)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button:discord.ui.Button):
        if interaction.user.id != self.___a.get_author():
            await interaction.response.send_message("You can't do that. You are not the author of this activity.", ephemeral=True, delete_after=15)
            return
        if self.___a.is_started():
            await interaction.response.send_message("You can't do that. The activity is already started.", ephemeral=True, delete_after=15)
            return
        global RUNNING_ACTIVITIES
        RUNNING_ACTIVITIES.pop(self.___a.get_creation_msg())
        await interaction.response.send_message("Activity cancelled.", ephemeral=True, delete_after=15)
        await interaction.message.delete()

