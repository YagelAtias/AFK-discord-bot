import os
from dotenv import load_dotenv
import discord
from discord.ext import tasks, commands
import datetime

load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
CHANNEL_ID = int(os.getenv('CHANNEL_ID'))
USER_ID = int(os.getenv("USER_ID"))

AWAY_ALERT_THRESHOLD_MINUTES = 15
intents = discord.Intents.default()
intents.members = True
intents.presences = True
intents.voice_states = True

bot = commands.Bot(command_prefix='!', intents=intents)

last_active = {}

# This event happens whenever the voice state changes on discord.
@bot.event
async def on_voice_state_update(member, before, after):
    if member.id == USER_ID:
        if before.channel != after.channel or before.self_mute != after.self_mute or before.self_deaf != after.self_deaf:
            last_active[USER_ID] = datetime.datetime.now()
