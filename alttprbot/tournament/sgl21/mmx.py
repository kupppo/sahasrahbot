import logging

from alttprbot import models
from alttprbot.tournament.core import TournamentConfig
from alttprbot_discord.bot import discordbot
from .sglcore import SGLCoreTournamentRace

class MMX(SGLCoreTournamentRace):
    async def configuration(self):
        guild = discordbot.get_guild(590331405624410116)
        return TournamentConfig(
            guild=guild,
            racetime_category='sgl',
            racetime_goal="Mega Man X",
            event_slug="sgl21mmx",
            audit_channel=discordbot.get_channel(774336581808291863),
            commentary_channel=discordbot.get_channel(631564559018098698),
            coop=False
        )