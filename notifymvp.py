from simplebot import send_discord_notification, run_bot
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

if __name__ == "__main__":
    # Start the bot in a separate thread
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.start()

    # Give the bot some time to start up
    time.sleep(5)

    # Run the odds processing
    run_odds_processing()

    # Keep the main thread alive
    bot_thread.join()
