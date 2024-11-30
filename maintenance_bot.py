from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import asyncio
import logging
import os
import aiohttp
import discord
from discord.ext import commands
from dotenv import load_dotenv

# Configure logging to save to a file
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', filename='maintenance_bot.log', filemode='a')
logger = logging.getLogger(__name__)

@dataclass
class TweetJob:
    """Independent tweet job container"""
    thread_id: int
    message_id: int
    thread_title: str
    initial_message: str
    image_path: Optional[str] = None
    status: str = "pending"
    error: Optional[str] = None
    created_at: datetime = datetime.now()

class MaintenanceBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.reactions = True
        super().__init__(command_prefix='!', intents=intents)
        
        # Role management config
        self.ROLES_CHANNEL_ID = 1115723672183902270
        self.emoji_to_role = {
            "🟦": 1115732713438195773,  # FanDuel
            "🟩": 1115733310048571444,  # DraftKings
            "🟪": 1115904331879825438,  # FreeBets
            "🎸": 1308479890647023778,  # Hard Rock Bet
            "🟨": 1116138362970058862,  # Caesars
            "🟥": 1116130539024437291,  # BetMGM
            "🟧": 1116130988909678682,  # WynnBet
            "🟫": 1116138843591168010,  # Tipico (US)
            "⚪️": 1132497073426681866,  # BetRivers
            "💚": 1116116559212056598,  # ESPN Bet
            "🔥": 1115734288114131055,  # Aces: High-stakes or advanced bettors
            "💵": 1115735250539118703,  # 5%: Users targeting 5% EV plays
            "🧊": 1115733528378875915,  # Nit: Risk-averse or conservative bettors
        }
        
        # Tweet processing config
        self.TWEET_CHANNELS = [
            1127408339236696114,  # Add your tweet channel IDs
            self.ROLES_CHANNEL_ID,  # Add roles channel to monitored channels
        ]
        self.TWEET_EMOJI = "🐤"  # baby_chick emoji
        self.TWEET_ROLE_ID = 1115730824059428946  # Required role to request tweets
        
        # Ensure images directory exists
        self.IMAGES_DIR = "tweet_images"
        os.makedirs(self.IMAGES_DIR, exist_ok=True)

    async def _handle_tweet_reaction(self, payload: discord.RawReactionActionEvent):
        """Handle tweet approval reactions"""
        try:
            # Only process baby_chick emoji reactions
            if str(payload.emoji) != self.TWEET_EMOJI:
                return

            # Check if user has required role
            guild = self.get_guild(payload.guild_id)
            member = payload.member or guild.get_member(payload.user_id)
            if not member or member.bot:
                return

            required_role = guild.get_role(self.TWEET_ROLE_ID)
            if not required_role or required_role not in member.roles:
                logger.warning(f"User {member.name} attempted to request tweet without required role")
                # Remove their reaction
                channel = self.get_channel(payload.channel_id)
                message = await channel.fetch_message(payload.message_id)
                await message.remove_reaction(self.TWEET_EMOJI, member)
                return

            # Start independent tweet processing
            asyncio.create_task(self._process_tweet_independently(payload.message_id, payload.channel_id))
                    
        except Exception as e:
            logger.error(f"Error processing tweet reaction: {e}")

    async def _process_tweet_independently(self, message_id: int, channel_id: int):
        """Independent tweet processing pipeline"""
        try:
            channel = self.get_channel(channel_id)
            message = await channel.fetch_message(message_id)
            thread = message.thread
            
            if not thread:
                logger.error("Tweet reaction must be on a thread message")
                await message.add_reaction('❌')
                return

            # Get the starter message using the property
            initial_message_content = thread.name  # fallback
            starter_message = thread.starter_message
            
            if starter_message:
                logger.info(f"Found starter message in cache")
                if starter_message.content.strip():
                    initial_message_content = starter_message.content.strip()
                    logger.info(f"Using starter message content: '{initial_message_content}'")
            else:
                # If not in cache, try to fetch it
                try:
                    starter_message = await thread.parent.fetch_message(thread.id)
                    if starter_message.content.strip():
                        initial_message_content = starter_message.content.strip()
                        logger.info(f"Using fetched starter message content: '{initial_message_content}'")
                except Exception as e:
                    logger.warning(f"Could not fetch starter message: {e}")
            
            job = TweetJob(
                thread_id=thread.id,
                message_id=message_id,
                thread_title=thread.name,
                initial_message=initial_message_content
            )
            logger.info(f"Created job with initial message: '{initial_message_content}'")
            logger.info(f"Processing tweet: {initial_message_content}")
            # 1. Find and download image
            image_path = await self._find_thread_image(thread)
            if not image_path:
                await message.add_reaction('❌')
                return
            
            job.image_path = image_path
            job.status = "image_downloaded"

            # 2. Process tweet (external API call)
            success = await self._process_tweet_api(job)
            if not success:
                await message.add_reaction('❌')
                return

            # 3. Mark as completed
            await message.add_reaction('✅')
            logger.info(f"Tweet processed successfully: {message_id} - {thread.name}")

        except Exception as e:
            logger.error(f"Error in tweet processing: {e}")
            await message.add_reaction('❌')

    async def _find_thread_image(self, thread) -> Optional[str]:
        """Find and download first image in thread"""
        try:
            async for msg in thread.history(limit=50):
                if msg.attachments:
                    for attachment in msg.attachments:
                        if attachment.content_type.startswith('image/'):
                            # Download image
                            image_data = await self._download_image(attachment)
                            if image_data:
                                # Save image
                                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                                filename = f"{thread.id}_{timestamp}.png"
                                filepath = os.path.join(self.IMAGES_DIR, filename)
                                 
                                with open(filepath, 'wb') as f:
                                    f.write(image_data)
                                 
                                return filepath
            
            logger.error("No image found in thread")
            return None

        except Exception as e:
            logger.error(f"Error finding thread image: {e}")
            return None

    async def _download_image(self, attachment: discord.Attachment) -> Optional[bytes]:
        """Download image from Discord attachment"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(attachment.url) as response:
                    if response.status == 200:
                        return await response.read()
                    else:
                        logger.error(f"Failed to download image: {response.status}")
                        return None
        except Exception as e:
            logger.error(f"Error downloading image: {e}")
            return None

    async def _process_tweet_api(self, job: TweetJob) -> bool:
        """Process tweet through external API"""
        try:
            # Your external API integration here
            # Example:
            # async with aiohttp.ClientSession() as session:
            #     async with session.post('your_api_endpoint', data={
            #         'image_path': job.image_path,
            #         'thread_id': job.thread_id
            #     }) as response:
            #         result = await response.json()
            #         return result['success']
            
            # Placeholder for API integration
            await asyncio.sleep(1)  # Simulate API call
            return True

        except Exception as e:
            logger.error(f"Error in tweet API processing: {e}")
            job.status = "failed"
            job.error = str(e)
            return False

    async def _handle_role_reaction(self, payload: discord.RawReactionActionEvent, add: bool):
        """Handle role assignment/removal reactions"""
        # Check if this emoji maps to a role
        role_id = self.emoji_to_role.get(str(payload.emoji))
        if not role_id:
            return

        try:
            guild = self.get_guild(payload.guild_id)
            
            # For removal events, we need to fetch the member since payload.member is None
            if add:
                member = payload.member
                if member.bot:  # Ignore bot reactions
                    return
            else:
                member = await guild.fetch_member(payload.user_id)
                if member.bot:  # Ignore bot reactions
                    return
            
            role = guild.get_role(role_id)
            if role:
                if add:
                    await member.add_roles(role)
                    logger.info(f"Added role {role.name} to {member.name}")
                else:
                    await member.remove_roles(role)
                    logger.info(f"Removed role {role.name} from {member.name}")
                
        except Exception as e:
            logger.error(f"Error handling role reaction: {e}")

    # Add these event handlers
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.channel_id in self.TWEET_CHANNELS:
            if payload.channel_id == self.ROLES_CHANNEL_ID:
                # Handle role reactions
                await self._handle_role_reaction(payload, add=True)
            else:
                # Handle tweet reactions
                await self._handle_tweet_reaction(payload)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        if payload.channel_id == self.ROLES_CHANNEL_ID:
            await self._handle_role_reaction(payload, add=False)

    @commands.Cog.listener()
    async def on_ready(self):
        logger.info(f'Bot is ready! Logged in as {self.user.name}')

def run_bot():
    # Add this line before accessing environment variables
    load_dotenv()
    
    # For debugging, you can add this:
    token = os.getenv('MAINTENANCE_BOT_TOKEN')
    if token is None:
        raise ValueError("MAINTENANCE_BOT_TOKEN not found in environment variables")
        
    bot = MaintenanceBot()
    bot.run(token)

if __name__ == "__main__":
    run_bot() 