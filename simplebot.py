import discord
from discord.ext import commands
import os
import asyncio
import queue

class SimpleBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix='!', intents=intents)
        self.channel_id = int(os.getenv('DISCORD_CHANNEL_ID'))
        self.notification_queue = queue.Queue()

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
            try:
                message = self.notification_queue.get_nowait()
                await self.send_notification(message)
            except queue.Empty:
                await asyncio.sleep(1)

bot = SimpleBot()

def send_discord_notification(message):
    bot.notification_queue.put(message)

def run_bot():
    bot.run(os.getenv('DISCORD_BOT_TOKEN'))
