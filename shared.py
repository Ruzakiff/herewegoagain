import threading
from queue import Queue
import time

class PriorityMessage:
    def __init__(self, message, timestamp):
        self.message = message
        self.timestamp = timestamp

    def __lt__(self, other):
        return self.timestamp > other.timestamp  # Reverse order for newest first

notification_queue = Queue()
newest_message = None
newest_message_lock = threading.Lock()

def send_discord_notification(message):
    global newest_message
    with newest_message_lock:
        if newest_message:
            notification_queue.put(PriorityMessage(newest_message, time.time()))
        newest_message = message