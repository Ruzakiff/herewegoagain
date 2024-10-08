import discord
from discord.ext import commands
import os
import asyncio
import threading
from shared import notification_queue, newest_message, newest_message_lock, PriorityMessage, send_discord_notification
from notifymvp import run_odds_processing

class realBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix='!', intents=intents)
        self.channel_id = int(os.getenv('DISCORD_CHANNEL_ID'))
        self.bg_task = None

    async def setup_hook(self):
        await self.add_cog(Commands(self))
        self.bg_task = self.loop.create_task(self.process_notifications())

    async def on_ready(self):
        print(f'{self.user} has connected to Discord!')
        print("Bot is ready!")

    async def process_notifications(self):
        global newest_message
        while True:
            with newest_message_lock:
                if newest_message:
                    await self.send_discord_notification(newest_message)
                    newest_message = None
            
            while not notification_queue.empty():
                message = notification_queue.get()
                await self.send_discord_notification(message.message)
                notification_queue.task_done()
            
            await asyncio.sleep(0.1)  # Short sleep when queue is empty

    async def send_discord_notification(self, message):
        channel = self.get_channel(self.channel_id)
        if channel:
            await channel.send(message)

class Commands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def ping(self, ctx):
        await ctx.send("Pong!")

    @commands.command()
    async def start_odds(self, ctx, rounds: int = 5):
        await ctx.send(f"Starting odds processing for {rounds} rounds...")
        # Import here to avoid circular import
        from notifymvp import run_odds_processing
        # Run odds processing in a separate thread to avoid blocking the bot
        threading.Thread(target=run_odds_processing, args=(rounds,)).start()
        await ctx.send("Odds processing started in the background.")

bot = realBot()

def run_bot():
    bot.run(os.getenv('DISCORD_BOT_TOKEN'))

if __name__ == "__main__":
    run_bot()


