import discord
from discord.ext import commands
import os
import asyncio
import threading

class PriorityMessage:
    def __init__(self, content, priority):
        self.content = content
        self.priority = priority

class SimpleBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix='!', intents=intents)
        self.channel_id = int(os.getenv('DISCORD_CHANNEL_ID'))
        self.message_queue = asyncio.Queue()
        self.message_lock = threading.Lock()
        self.current_priority = 0
        self.loop = None

    async def on_ready(self):
        print(f'{self.user} has connected to Discord!')
        print("Bot is ready!")
        self.bg_task = self.loop.create_task(self.process_notifications())

    @commands.command()
    async def ping(self, ctx):
        await ctx.send("Pong!")

    async def send_notification(self, message):
        channel = self.get_channel(self.channel_id)
        if channel:
            await channel.send(message)

    async def process_notifications(self):
        while True:
            priority, message = await self.message_queue.get()
            await self.send_notification(message.content)
            self.message_queue.task_done()

bot = SimpleBot()

def run_bot():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    bot.loop = loop
    bot.run(os.getenv('DISCORD_BOT_TOKEN'))

def send_discord_notification(message):
    if bot.loop is None:
        raise RuntimeError("Bot is not running. Call run_bot() first.")
    
    with bot.message_lock:
        bot.current_priority -= 1  # Lower priority number means higher priority
        priority_message = PriorityMessage(message, bot.current_priority)
        future = asyncio.run_coroutine_threadsafe(bot.message_queue.put((bot.current_priority, priority_message)), bot.loop)
        future.result()  # Ensure the message is added to the queue

