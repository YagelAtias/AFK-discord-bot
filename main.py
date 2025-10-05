import os
import json
from dotenv import load_dotenv
import discord
from discord.ext import tasks, commands
import datetime

load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
CHANNEL_ID = int(os.getenv('CHANNEL_ID'))
USER_ID = int(os.getenv("USER_ID"))
FRIENDS = os.getenv("FRIENDS").split(',')

AWAY_ALERT_THRESHOLD_MINUTES = 15
LOOP_CHECK_INTERVAL_MINUTES = 5

intents = discord.Intents.default()
intents.members = True
intents.presences = True
intents.voice_states = True

bot = commands.Bot(command_prefix='!', intents=intents)


def save_data(data, filename):
    with open(filename, 'w') as f:
        json.dump(data, f)


def load_data(filename):
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            return json.load(f)
    return {}


last_active = load_data("last_active.json")


def create_message():
    friend_mentions = [f"<@{friend.strip()}>" for friend in FRIENDS]
    if not friend_mentions:
        return f"Hey, <@{USER_ID}> hasn't been here for the past {AWAY_ALERT_THRESHOLD_MINUTES} minutes..."
    mentions_string = ", ".join(friend_mentions[:-1])
    if len(friend_mentions) > 1:
        mentions_string += f" and {friend_mentions[-1]}"
    else:
        mentions_string = friend_mentions[0]
    return (f"Hey {mentions_string}, don't get baited! <@{USER_ID}> hasn't been here for the past "
            f"{AWAY_ALERT_THRESHOLD_MINUTES} minutes...")


# This event happens whenever the voice state changes on discord.
@bot.event
async def on_voice_state_update(member, before, after):
    if member.id == USER_ID:
        if before.channel != after.channel or before.self_mute != after.self_mute or before.self_deaf != after.self_deaf:
            last_active[USER_ID] = datetime.datetime.now().isoformat()
            save_data(last_active, "last_active.json")


# Every few minutes check if the user is active, and if not, alert his friends.
@tasks.loop(minutes=LOOP_CHECK_INTERVAL_MINUTES)
async def check_user_status():
    await bot.wait_until_ready()
    member = bot.get_user(USER_ID)
    if member:
        voice_channel = discord.utils.get(bot.get_all_channels(), type=discord.ChannelType.voice, members=[member])
        if voice_channel and USER_ID in last_active:
            last_active_time = datetime.datetime.fromisoformat(last_active[USER_ID])
            time_inactive = datetime.datetime.now() - last_active_time
            if time_inactive.total_seconds() > AWAY_ALERT_THRESHOLD_MINUTES * 60:
                channel = bot.get_channel(CHANNEL_ID)
                if channel:
                    await channel.send(create_message())
                # Reset the last active time to prevent spamming
                del last_active[USER_ID]
                save_data(last_active, "last_active.json")


@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    check_user_status.start()


bot.run(DISCORD_TOKEN)
