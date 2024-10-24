import discord
from discord.ext import commands
import os
import asyncio
import threading
from shared import notification_queue, send_discord_notification
from fetch3 import main as fetch_main, AggressiveTokenBucket, load_bookmaker_regions
import logging
from dotenv import load_dotenv
import json

# Load environment variables from .env file
load_dotenv()

# Set up logging at the top of your file
logging.basicConfig(level=logging.DEBUG, filename='realbot.log', filemode='a',
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


role_to_id = {
    "Fanduel": 1115732713438195773,
    "FreeBets": 1115904331879825438,
    "Barstool": 1116116559212056598,
    "Superbook":1116130466773344317,
    "Betmgm":1116130539024437291,
    "Wynnbet":1116130988909678682,
    "Draftkings":1116130988909678682,
    "Williamhill_us":1116138362970058862,
    "Tipico_us":1116138843591168010,
    "Aces":1115734288114131055,
    "5%":1115735250539118703,
    "nit": 1115733528378875915,
    "tab": 1298784594140594197
    # Add more mappings as needed
}
sports_to_id = {
    "NFL": 1127408339236696114,
    "NBA": 1
    # Add more sports and their corresponding IDs here as needed
}


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

    
    async def send_discord_notification(self, json_message):
        channel = self.get_channel(self.channel_id)
        if channel:
            try:
                # Parse the JSON message
                parsed_data = json.loads(json_message)
                
                # Create a concise message for the main channel
                main_message = self.create_main_message(parsed_data)
                
                # Send the main message and create a thread
                sent_message = await channel.send(main_message)
                
                # Create a thread for the sent message
                thread_name = f"Notification {sent_message.id}"
                thread = await sent_message.create_thread(name=thread_name, auto_archive_duration=1440)
                
                # Create a detailed message for the thread
                thread_message = self.create_thread_message(parsed_data)
                
                # Send the detailed message in the thread
                await thread.send(thread_message)
                
                # Log the successful message send
                logger.info(f"Message sent successfully and thread created: {main_message[:50]}...")
                
            except Exception as e:
                logger.error(f"Failed to send message: {str(e)}")
                # Put the message back in the queue if sending fails
                await notification_queue.put(json_message)
        else:
            logger.error(f"Channel not found: {self.channel_id}")

    def create_main_message(self, data):
        return (
            f"🏈 NFL Positive EV Detected!\n"
            f"Event: {data['event']}\n"
            f"Market: {data['market']}\n"
            f"Player: {data['player']}\n"
            f"Edge: {data['edge']:.2f}%\n"
            f"EV Difference: {data['ev_difference']:.4f}"
        )

    def create_thread_message(self, data):
        message = [
            "Detailed Calculation Steps:",
            "1. Sharp Prices:",
            "   Yes prices:",
            *[f"     {price['bookmaker']}: {price['american']} ({price['decimal']:.4f})" for price in data['sharp_prices']['yes']],
            f"   Final Sharp Yes: {data['sharp_prices']['final_sharp_yes']['american']} ({data['sharp_prices']['final_sharp_yes']['decimal']:.4f})",
            "   No prices:",
            *[f"     {price['bookmaker']}: {price['american']} ({price['decimal']:.4f})" for price in data['sharp_prices']['no']],
            f"   Final Sharp No: {data['sharp_prices']['final_sharp_no']['american']} ({data['sharp_prices']['final_sharp_no']['decimal']:.4f})",
            f"2. Power Devig: Yes: {data['devig']['power']['yes']:.4f}, No: {data['devig']['power']['no']:.4f}",
            f"3. Mult Devig: Yes: {data['devig']['mult']['yes']:.4f}, No: {data['devig']['mult']['no']:.4f}",
            "4. Ground Truth:",
            f"   Yes: {data['ground_truth']['yes']['decimal']:.4f} ({data['ground_truth']['yes']['american']})",
            f"   No: {data['ground_truth']['no']['decimal']:.4f} ({data['ground_truth']['no']['american']})",
            f"5. Base price ({data['base_price']['bookmaker']}): {data['base_price']['american']} ({data['base_price']['decimal']:.4f})",
            "6. Implied probabilities:",
            f"   Ground Truth: {data['implied_probabilities']['ground_truth']:.4f}",
            f"   Base: {data['implied_probabilities']['base']:.4f}",
            f"7. Edge: {data['edge']:.2f}%",
            f"8. EV Difference: {data['ev_difference']:.4f}"
        ]
        return "\n".join(message)

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
