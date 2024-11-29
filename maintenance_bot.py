import discord
from discord.ext import commands
from typing import Dict
import logging
import os
from dotenv import load_dotenv
import aiohttp
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MaintenanceBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.reactions = True
        super().__init__(command_prefix='!', intents=intents)
        
        # Role management config
        self.ROLES_CHANNEL_ID = 1115723672183902270
        self.emoji_to_role: Dict[str, int] = {
            "🔵": 123456789,  # Replace with actual role IDs
            "🔴": 987654321,
        }
        
        # Tweet processing config
        self.TWEET_CHANNELS = [
            1127408339236696114,  # Add your tweet channel IDs
        ]
        self.TWEET_EMOJI = "🐤"  # baby_chick emoji
        self.TWEET_ROLE_ID = 1115730824059428946  # Required role to request tweets
        self.pending_tweets = {}
        
        # Ensure images directory exists
        self.IMAGES_DIR = "tweet_images"
        os.makedirs(self.IMAGES_DIR, exist_ok=True)

    async def setup_hook(self):
        """Initialize bot components"""
        await self.add_cog(MaintenanceCommands(self))
        logger.info("Bot systems initialized")

    async def on_ready(self):
        logger.info(f"Bot connected as {self.user}")

    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        """Central reaction handler"""
        # Handle role assignments
        if payload.channel_id == self.ROLES_CHANNEL_ID:
            await self._handle_role_reaction(payload, add_role=True)
        
        # Handle tweet processing
        elif payload.channel_id in self.TWEET_CHANNELS:
            await self._handle_tweet_reaction(payload)

    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        """Handle role removal"""
        if payload.channel_id == self.ROLES_CHANNEL_ID:
            await self._handle_role_reaction(payload, add_role=False)

    async def _handle_role_reaction(self, payload: discord.RawReactionActionEvent, add_role: bool):
        """Handle role assignment reactions"""
        try:
            # Skip bot reactions
            if payload.member and payload.member.bot:
                return

            emoji_str = str(payload.emoji)
            role_id = self.emoji_to_role.get(emoji_str)
            if not role_id:
                return

            guild = self.get_guild(payload.guild_id)
            member = payload.member or guild.get_member(payload.user_id)
            if not member or member.bot:
                return

            role = guild.get_role(role_id)
            if not role:
                logger.error(f"Role {role_id} not found!")
                return

            if add_role:
                await member.add_roles(role, reason="Reaction role")
                logger.info(f"Added role {role.name} to {member.name}")
            else:
                await member.remove_roles(role, reason="Reaction role")
                logger.info(f"Removed role {role.name} from {member.name}")

        except discord.Forbidden:
            logger.error("Missing permissions to manage roles!")
        except Exception as e:
            logger.error(f"Error in role management: {e}")

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

            message_id = payload.message_id
            
            # Check if we haven't processed this message yet
            if message_id not in self.pending_tweets:
                self.pending_tweets[message_id] = True
                channel = self.get_channel(payload.channel_id)
                message = await channel.fetch_message(message_id)
                await self._process_tweet(message)
                logger.info(f"Tweet requested for message {message_id} by {member.name}")
                    
        except Exception as e:
            logger.error(f"Error processing tweet reaction: {e}")

    async def _process_tweet(self, message: discord.Message):
        """Process thread for tweeting"""
        try:
            # Get the thread
            thread = message.thread
            if not thread:
                logger.error("Tweet reaction must be on a thread message")
                await message.add_reaction('❌')
                return

            # Find the first message with an image in the thread
            async for msg in thread.history(limit=50):  # Adjust limit as needed
                if msg.attachments:
                    for attachment in msg.attachments:
                        if attachment.content_type.startswith('image/'):
                            # Download the image
                            image_data = await self._download_image(attachment)
                            if image_data:
                                # Generate filename with timestamp
                                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                                filename = f"{thread.id}_{timestamp}.png"
                                filepath = os.path.join(self.IMAGES_DIR, filename)
                                
                                # Save the image
                                with open(filepath, 'wb') as f:
                                    f.write(image_data)
                                
                                logger.info(f"Saved image for tweet: {filepath}")
                                await message.add_reaction('✅')
                                return

            # If we get here, no image was found
            logger.error("No image found in thread")
            await message.add_reaction('❌')
            
        except Exception as e:
            logger.error(f"Error processing tweet: {e}")
            await message.add_reaction('❌')

    async def _download_image(self, attachment: discord.Attachment) -> bytes:
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

class MaintenanceCommands(commands.Cog):
    def __init__(self, bot: MaintenanceBot):
        self.bot = bot

    @commands.has_permissions(administrator=True)
    @commands.command()
    async def status(self, ctx):
        """Check bot status"""
        status_message = (
            "🤖 **Bot Status**\n"
            f"Role Channel: {self.bot.ROLES_CHANNEL_ID}\n"
            f"Tweet Channels: {len(self.bot.TWEET_CHANNELS)}\n"
            f"Processed Tweets: {len(self.bot.pending_tweets)}"
        )
        await ctx.send(status_message)

def run_bot():
    load_dotenv()
    bot = MaintenanceBot()
    bot.run(os.getenv('MAINTENANCE_BOT_TOKEN'))

if __name__ == "__main__":
    run_bot() 