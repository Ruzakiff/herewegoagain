import discord
from discord.ext import commands
from typing import Dict

class RoleBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.reactions = True
        super().__init__(command_prefix='!', intents=intents)
        
        # Channel to monitor for role reactions
        self.ROLES_CHANNEL_ID = 1115723672183902270
        
        # Map emojis to role IDs - customize these!
        self.emoji_to_role: Dict[str, int] = {
            "🔵": 123456789,  # Replace with actual role IDs
            "🔴": 987654321,
            # Add more emoji -> role_id mappings
        }

    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        """Handle reaction adds"""
        if payload.channel_id != self.ROLES_CHANNEL_ID:
            return
        await self._handle_reaction(payload, add_role=True)

    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        """Handle reaction removes"""
        if payload.channel_id != self.ROLES_CHANNEL_ID:
            return
        await self._handle_reaction(payload, add_role=False)

    async def _handle_reaction(self, payload: discord.RawReactionActionEvent, add_role: bool):
        """Core reaction handling logic"""
        # Ignore bot reactions
        if payload.member and payload.member.bot:
            return

        # Get the role ID for this emoji
        emoji_str = str(payload.emoji)
        role_id = self.emoji_to_role.get(emoji_str)
        if not role_id:
            return

        # Get guild and member
        guild = self.get_guild(payload.guild_id)
        if not guild:
            return
        
        # For role removal, we need to fetch the member
        member = payload.member or guild.get_member(payload.user_id)
        if not member or member.bot:
            return

        # Get role
        role = guild.get_role(role_id)
        if not role:
            print(f"Role {role_id} not found!")
            return

        try:
            if add_role:
                await member.add_roles(role, reason="Reaction role")
            else:
                await member.remove_roles(role, reason="Reaction role")
        except discord.Forbidden:
            print(f"Missing permissions to manage roles!")
        except Exception as e:
            print(f"Error managing role: {e}")

    async def on_ready(self):
        print(f'{self.user} has connected to Discord!')
        print("Bot is ready!")

def run_bot():
    bot = RoleBot()
    bot.run('YOUR_BOT_TOKEN')

if __name__ == "__main__":
    run_bot()