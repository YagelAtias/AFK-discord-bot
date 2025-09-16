import os
from dotenv import load_dotenv
import discord
from discord.ext import tasks, commands
import datetime
load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
CHANNEL_ID = int(os.getenv('CHANNEL_ID'))
USER_ID = int(os.getenv("USER_ID"))
