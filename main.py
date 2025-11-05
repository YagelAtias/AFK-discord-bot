import os
import json
from dotenv import load_dotenv
import discord
from discord.ext import tasks, commands
import datetime
from discord.utils import utcnow
from discord import AuditLogAction

load_dotenv()

# Env parsing with minimal safety
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
CHANNEL_ID_STRING = os.getenv('CHANNEL_ID')
USER_ID_STRING = os.getenv('USER_ID')
FRIENDS_STRING = os.getenv('FRIENDS') or ''

try:
    CHANNEL_ID = int(CHANNEL_ID_STRING)
    USER_ID = int(USER_ID_STRING)
except (TypeError, ValueError):
    raise RuntimeError("CHANNEL_ID and USER_ID must be provided as integers in .env")

FRIENDS = [x.strip() for x in FRIENDS_STRING.split(',') if x.strip()]

AWAY_ALERT_THRESHOLD_MINUTES = 15
LOOP_CHECK_INTERVAL_MINUTES = 5

# Use a consistent string key for JSON
KEY = str(USER_ID)

intents = discord.Intents.default()
intents.members = True
intents.presences = True
intents.voice_states = True

bot = commands.Bot(command_prefix='!', intents=intents)


def save_data(data, filename):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f)


def load_data(filename):
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


last_active = load_data("last_active.json")

# Debounce: avoid rewriting the timestamp too often (e.g., multiple state flaps) within X seconds
DEBOUNCE_SECONDS = 2


def set_last_active():
    now = utcnow()
    prev_iso = last_active.get(KEY)
    if prev_iso:
        try:
            prev = datetime.datetime.fromisoformat(prev_iso)
        except ValueError:
            prev = None
        if prev is not None and (now - prev).total_seconds() < DEBOUNCE_SECONDS:
            return  # debounce
    last_active[KEY] = now.isoformat()
    save_data(last_active, "last_active.json")


def create_message():
    mentions = [f"<@{fid}>" for fid in FRIENDS]
    if not mentions:
        who = f"<@{USER_ID}>"
    elif len(mentions) == 1:
        who = mentions[0]
    else:
        who = ", ".join(mentions[:-1]) + f" and {mentions[-1]}"
    return (
        f"Hey {who}, don't get baited! <@{USER_ID}> hasn't been here for the past "
        f"{AWAY_ALERT_THRESHOLD_MINUTES} minutes..."
    )


async def was_moved_by_someone(guild: discord.Guild, target_id: int, within_seconds: int = 3) -> bool:
    """
    Returns True if audit logs show a recent member_move targeting the user.
    Requires the bot to have the 'View Audit Log' permission.
    """
    try:
        async for entry in guild.audit_logs(limit=5, action=AuditLogAction.member_move):
            if getattr(entry.target, "id", None) == target_id:
                if (utcnow() - entry.created_at).total_seconds() <= within_seconds:
                    return True
    except discord.Forbidden:
        # Cannot read audit logs; assume user-initiated elsewhere
        return False
    except discord.HTTPException:
        # Transient API issue; fail open (treat as user-initiated)
        return False
    return False


@bot.event
async def on_voice_state_update(member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
    if member.id != USER_ID:
        return

    # Ignore AFK auto-moves entirely
    if after.afk:
        return

    user_initiated = False

    # These toggles are always user-driven signals of presence
    if before.self_mute != after.self_mute:
        user_initiated = True
    if before.self_deaf != after.self_deaf:
        user_initiated = True
    if getattr(before, 'self_stream', False) != getattr(after, 'self_stream', False):
        user_initiated = True
    if getattr(before, 'self_video', False) != getattr(after, 'self_video', False):
        user_initiated = True

    # Channel change can be user-initiated or external
    if before.channel != after.channel and after.channel is not None:
        guild = after.channel.guild
        moved_by_other = await was_moved_by_someone(guild, USER_ID)
        if not moved_by_other:
            user_initiated = True

    if user_initiated:
        set_last_active()


@tasks.loop(minutes=LOOP_CHECK_INTERVAL_MINUTES)
async def check_user_status():
    # Use the alert channel to identify the guild we care about
    channel = bot.get_channel(CHANNEL_ID)
    if channel is None or not hasattr(channel, "guild"):
        return

    guild = channel.guild
    member = guild.get_member(USER_ID)
    if member is None:
        return

    # Only alert if the user is currently in a voice channel
    if member.voice is None or member.voice.channel is None:
        return

    if KEY not in last_active:
        return

    try:
        last_active_time = datetime.datetime.fromisoformat(last_active[KEY])
    except ValueError:
        # Corrupt/malformed timestamp; reset it to now and skip this cycle
        set_last_active()
        return

    # Normalize 'now' to the same tz awareness as the stored timestamp
    if last_active_time.tzinfo is None:
        now = datetime.datetime.utcnow()
    else:
        now = datetime.datetime.now(tz=last_active_time.tzinfo)

    time_inactive = now - last_active_time
    if time_inactive.total_seconds() > AWAY_ALERT_THRESHOLD_MINUTES * 60:
        await channel.send(create_message())
        # Reset the last active time to prevent spamming
        if KEY in last_active:
            del last_active[KEY]
            save_data(last_active, "last_active.json")


@check_user_status.before_loop
async def before_check_user_status():
    await bot.wait_until_ready()


@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    if not check_user_status.is_running():
        check_user_status.start()


bot.run(DISCORD_TOKEN)
