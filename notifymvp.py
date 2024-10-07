from simplebot import send_discord_notification, run_bot, bot
import time
import random
import threading

def process_odds():
    # Simulate odds processing
    time.sleep(2)  # Simulate some processing time
    if random.random() > 0.5:  # 50% chance of finding a "high value bet"
        send_discord_notification(f"High value bet found! EV: {random.uniform(3, 10):.2f}%")

def run_odds_processing():
    print("Starting odds processing simulation...")
    for _ in range(5):  # Simulate 5 rounds of processing
        process_odds()
        time.sleep(1)  # Wait a bit between rounds
    print("Simulation complete.")

def wait_for_bot_ready():
    while bot.loop is None or not bot.is_ready():
        time.sleep(0.1)
    print("Bot is ready!")

if __name__ == "__main__":
    # Start the bot in a separate thread
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.start()

    # Wait for the bot to be ready
    wait_for_bot_ready()

    # Run the odds processing
    run_odds_processing()

    # Keep the main thread alive
    bot_thread.join()
