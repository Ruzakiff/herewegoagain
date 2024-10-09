import threading
from queue import LifoQueue  # Last-In-First-Out Queue
import asyncio
import time
import logging

logger = logging.getLogger(__name__)

# Save logger output to a file
file_handler = logging.FileHandler('shared.log')
file_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)
class PriorityMessage:
    def __init__(self, priority, message):
        self.priority = priority
        self.message = message

    def __lt__(self, other):
        return self.priority < other.priority  # Reverse order for newest first

notification_queue = asyncio.LifoQueue()

async def send_discord_notification(message):
    await notification_queue.put(message)
