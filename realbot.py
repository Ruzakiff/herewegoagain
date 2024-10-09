import discord
from discord.ext import commands
import os
import asyncio
import threading
from shared import notification_queue, send_discord_notification
from fetch3 import main as fetch_main, AggressiveTokenBucket, load_bookmaker_regions
import logging

# Set up logging at the top of your file
logging.basicConfig(level=logging.DEBUG, filename='realbot.log', filemode='a',
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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
        while True:
            try:
                message = notification_queue.get_nowait()
                await self.send_discord_notification(message)
                notification_queue.task_done()
            except asyncio.QueueEmpty:
                await asyncio.sleep(0.1)

    async def send_discord_notification(self, message):
        channel = self.get_channel(self.channel_id)
        if channel:
            try:
                await channel.send(message)
                print(f"Message sent successfully: {message[:50]}...")
            except Exception as e:
                print(f"Failed to send message: {str(e)}")
                # Put the message back in the queue if sending fails
                await notification_queue.put(message)
        else:
            print(f"Channel not found: {self.channel_id}")

class Commands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def ping(self, ctx):
        await ctx.send("Pong!")

    @commands.command()
    async def start_odds(self, ctx, sport: str = 'americanfootball_nfl'):
        await ctx.send(f"Starting odds processing for {sport}...")
        
        # Run odds processing in a separate thread to avoid blocking the bot
        threading.Thread(target=asyncio.run, args=(self.run_odds_processing(sport),)).start()
        
        await ctx.send("Odds processing started in the background.")

    async def run_odds_processing(self, sport):
        # Set up the parameters for fetch_main
        market_bookmaker_combinations = [
            ('player_anytime_td', ['fliff', 'tab', 'espnbet', 'pinnacle']),
            ('player_last_td', ['fliff', 'tab', 'espnbet', 'pinnacle'])
        ]
        principal_bookmaker = 'fliff'
        base_bookmaker = 'tab'
        optional_principals = ['pinnacle', 'espnbet']

        # Load bookmaker regions
        BOOKMAKER_REGIONS = await load_bookmaker_regions()

        # Set up token bucket
        rate = 10  # tokens per second
        capacity = 50  # maximum tokens
        token_bucket = AggressiveTokenBucket(rate, capacity)

        # Run the main function from fetch3
        await fetch_main(sport, market_bookmaker_combinations, principal_bookmaker, base_bookmaker, optional_principals, BOOKMAKER_REGIONS, token_bucket)

bot = realBot()

def run_bot():
    bot.run(os.getenv('DISCORD_BOT_TOKEN'))

if __name__ == "__main__":
    run_bot()


