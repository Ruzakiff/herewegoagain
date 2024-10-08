import discord
from discord.ext import commands
import os
import asyncio
import threading
from queue import Queue
import time

class PriorityMessage:
    def __init__(self, message, timestamp):
        self.message = message
        self.timestamp = timestamp

    def __lt__(self, other):
        return self.timestamp > other.timestamp  # Reverse order for newest first

class realBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix='!', intents=intents)
        self.channel_id = int(os.getenv('DISCORD_CHANNEL_ID'))
        self.notification_queue = Queue()
        self.bg_task = None
        self.is_sending = threading.Lock()
        self.newest_message = None
        self.newest_message_lock = threading.Lock()

    async def setup_hook(self):
        # Add this method to load commands
        await self.add_cog(Commands(self))
        self.bg_task = self.loop.create_task(self.process_notifications())

    async def on_ready(self):
        print(f'{self.user} has connected to Discord!')
        print("Bot is ready!")

    async def process_notifications(self):
        while True:
            with self.newest_message_lock:
                if self.newest_message:
                    await self.send_discord_notification(self.newest_message)
                    self.newest_message = None
            
            while not self.notification_queue.empty():
                message = self.notification_queue.get()
                await self.send_discord_notification(message.message)
                self.notification_queue.task_done()
            
            await asyncio.sleep(0.1)  # Short sleep when queue is empty

    async def send_discord_notification(self, message):
        channel = self.get_channel(self.channel_id)
        if channel:
            await channel.send(message)

    def add_notification(self, message):
        with self.newest_message_lock:
            if self.is_sending.locked():
                # If currently sending, update newest_message or add to queue
                if self.newest_message:
                    self.notification_queue.put(PriorityMessage(self.newest_message, time.time()))
                self.newest_message = message
            else:
                # If not sending, send immediately
                with self.is_sending:
                    asyncio.run_coroutine_threadsafe(self.send_discord_notification(message), self.loop)

class Commands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def ping(self, ctx):
        await ctx.send("Pong!")

bot = realBot()

def run_bot():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    bot.loop = loop
    bot.run(os.getenv('DISCORD_BOT_TOKEN'))

def send_notification(message):
    if bot.loop is None:
        raise RuntimeError("Bot is not running. Call run_bot() first.")
    
    bot.add_notification(message)
run_bot()
# Usage from any thread
send_notification("Your message here")


