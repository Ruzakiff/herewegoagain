import asyncio
import discord
from discord.ext import commands
import os

class DiscordNotifier:
    def __init__(self):
        self.bot = commands.Bot(command_prefix='!', intents=discord.Intents.default())
        self.queue = asyncio.Queue()
        self.channel_id = int(os.getenv('DISCORD_CHANNEL_ID'))

    async def start(self):
        await self.bot.start(os.getenv('DISCORD_BOT_TOKEN'))

    async def send_notification(self, message):
        await self.queue.put(message)

    async def process_queue(self):
        while True:
            message = await self.queue.get()
            channel = self.bot.get_channel(self.channel_id)
            if channel:
                await channel.send(message)
            self.queue.task_done()

notifier = DiscordNotifier()

@notifier.bot.event
async def on_ready():
    print(f'{notifier.bot.user} has connected to Discord!')
    asyncio.create_task(notifier.process_queue())

async def run_discord_bot():
    await notifier.start()

def send_discord_notification(message):
    asyncio.create_task(notifier.send_notification(message))