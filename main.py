import os
from dotenv import load_dotenv
import discord
from discord.ext import tasks, commands
import datetime

load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
CHANNEL_ID = int(os.getenv('CHANNEL_ID'))
USER_ID = int(os.getenv("USER_ID"))
FRIEND_1 = int(os.getenv("FRIEND_1"))
FRIEND_2 = int(os.getenv("FRIEND_2"))

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


# Every 5 minutes check if the user is active, and if not, alert his friends.
@tasks.loop(minutes=5)
async def check_user_status():
    await bot.wait_until_ready()

    member = bot.get_user(USER_ID)

    if member:
        voice_channel = discord.utils.get(bot.get_all_channels(), type=discord.ChannelType.voice, members=[member])

        if voice_channel and USER_ID in last_active:
            time_inactive = datetime.datetime.now() - last_active[USER_ID]

            if time_inactive.total_seconds() > AWAY_ALERT_THRESHOLD_MINUTES * 60:
                channel = bot.get_channel(CHANNEL_ID)
                if channel:
                    message = (
                        f"Hey <@{FRIEND_1}> and <@{FRIEND_2}>, don't get baited! <@{USER_ID}> wasn't here for the past"
                        f" {AWAY_ALERT_THRESHOLD_MINUTES} minutes...")
                    await channel.send(message)

                # Reset the last active time to prevent spamming
                del last_active[USER_ID]


@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    check_user_status.start()


bot.run(DISCORD_TOKEN)
