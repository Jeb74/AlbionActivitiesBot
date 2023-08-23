from datetime import datetime, timedelta

import discord
import pytz

ACTIVITY_COLOR = {
    "Fighting": discord.Color(801472),
    "Ganking": discord.Color(12585996),
    "Hellgate": discord.Color(6578786)
}


class Activity:
    def __init__(self, *, author: int = None, _type: str = None, mnp: int = None, mxp: int = None, creation_time: datetime = None, difference: timedelta = None):
        self.___author: int = author
        self.___type: str = _type
        self.___mnp: int = mnp
        self.___mxp: int = mxp
        self.___participants: list[tuple[int:datetime]] = [(self.___author, creation_time)]
        self.___creation_time: datetime = creation_time
        self.___starts_at: datetime = creation_time + difference
        self.___shotcaller: int = None
        self.___splitter: int = None
        self.___profit = "?"
        self.___ltb = "?"
        self.___is_closed: bool = False
        self.___closed_at: datetime = None
        # GUILD, CHANNEL, MESSAGE
        self.___guild: int = None
        self.___creation_channel: int = None
        self.___creation_msg_id: int = None
        self.___split_msg_id: int = None

    def set_creation_msg(self, msg_id):
        self.___creation_msg_id = msg_id

    def set_split_msg(self, msg_id):
        self.___split_msg_id = msg_id

    def is_started(self):
        return (self.___starts_at - datetime.now(pytz.timezone("Europe/Rome"))).total_seconds() < 0

    def get_creation_msg(self):
        return self.___creation_msg_id

    def get_split_msg(self):
        return self.___split_msg_id

    def add_participant(self, _id: int, time: datetime):
        self.___participants.append((_id, time))

    def remove_participant(self, _id: int):
        for i in range(len(self.___participants)):
            if self.___participants[i][0] == _id:
                self.___participants.pop(i)
                return

    def get_author(self):
        return self.___author

    def close(self):
        self.___is_closed = True
        self.___closed_at = datetime.now(pytz.timezone("Europe/Rome"))

    def is_closed(self):
        return self.___is_closed

    def set_shotcaller(self, shotcaller_id):
        self.___shotcaller = shotcaller_id

    def set_splitter(self, splitter_id):
        self.___splitter = splitter_id

    def get_starting_time(self):
        return self.___starts_at

    def get_participants(self):
        return self.___participants

    def get_max_players(self):
        return self.___mxp

    def get_min_players(self):
        return self.___mnp

    def get_type(self):
        return self.___type

    def get_creation_time(self):
        return self.___creation_time

    def get_shotcaller(self):
        return self.___shotcaller

    def get_splitter(self):
        return self.___splitter

    def reached_max(self):
        return isinstance(self.___mxp, int) and len(self.___participants) == self.___mxp

    def reached_min(self):
        return self.___mnp <= len(self.___participants)

    def all_set(self):
        return self.___shotcaller is not None and self.___splitter is not None

    def set_profit(self, profit: str):
        self.___profit = profit

    def set_loot_table(self, table: str):
        self.___ltb = table

    def set_guild(self, guild: int):
        self.___guild = guild

    def set_channel(self, channel: int):
        self.___creation_channel = channel

    def get_id(self):
        return hash((self.___guild, self.___creation_channel, self.___creation_msg_id))

    def __dict__(self):
        return {i.removeprefix("___"): getattr(self, i) for i in dir(Activity) if i.startswith("___")}

    def to_embed(self):
        embed = discord.Embed()
        global ACTIVITY_COLOR
        if (datetime.now(pytz.timezone("Europe/Rome")) - self.___starts_at).total_seconds() < 0:
            embed.title = f"{self.___type} activity."
            embed.colour = ACTIVITY_COLOR.get(self.___type)
            embed.add_field(name="Created at", value=f"<t:{int(self.___creation_time.timestamp())}>")
            embed.add_field(name="by", value=f"<@{self.___author}>")
            embed.add_field(name="Min Player", value=f"{self.___mnp}", inline=False)
            embed.add_field(name="Max Player", value=f"{self.___mxp}")
            embed.add_field(name="Starting in", value=f"<t:{int(self.___starts_at.timestamp())}:R>", inline=False)
            embed.add_field(name="Currently registered players", value="\n".join([f"<@{i[0]}> - {i[1].strftime('%H:%M')}" for i in self.___participants]), inline=False)
        else:
            embed.title = f"LOOT TABLE: {self.___ltb} - PROFIT: {self.___profit}"
            embed.colour = ACTIVITY_COLOR.get(self.___type)
            embed.add_field(name="Activity", value=self.___type, inline=False)
            embed.add_field(name="Date of activity request", value=f"<t:{int(self.___creation_time.timestamp())}>", inline=False)
            embed.add_field(name="Min Players", value=f"{self.___mnp} ✔")
            embed.add_field(name="Max Players", value=f"{self.___mxp} {' ✔' if isinstance(self.___mxp, int) and self.___mxp == len(self.___participants) else ' ✖'}")
            embed.add_field(name="Participants", value="\n".join([f"{i+1} - <@{self.___participants[i][0]}> " + f"# {self.___participants[i][1].strftime('%H:%M')}" for i in range(len(self.___participants))]), inline=False)
            embed.add_field(name="Shotcaller", value=f"<@{self.___shotcaller}>" if self.___shotcaller is not None else "Not voted", inline=False)
            embed.add_field(name="Started", value=f"<t:{int(self.___starts_at.timestamp())}:R>", inline=False)
            embed.add_field(name="Splitted", value="Not yet" if not self.___is_closed else f"<t:{int(self.___closed_at.timestamp())}>")
            embed.add_field(name="by", value="None" if not self.___is_closed else f"<@{self.___splitter}>")
        return embed

    @staticmethod
    def fromDict(dictionary: dict):
        keyset = dictionary.keys()
        attributes = [i for i in dir(Activity) if i.startswith("___")]
        tmp_attr = map(lambda x: x.removeprefix("___"), attributes)
        if all([i in tmp_attr for i in keyset]):
            a = Activity()
            for k in keyset:
                setattr(a, "___" + k, dictionary.get(k))
            return a
        return None





