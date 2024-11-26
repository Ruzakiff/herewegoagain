import time
import random
from shared import send_discord_notification

def process_odds():
    print("Processing odds...")
    time.sleep(2)  # Simulate some processing time
    if random.random() > 0.5:  # 50% chance of finding a "high value bet"
        send_discord_notification(f"High value bet found! EV: {random.uniform(3, 10):.2f}%")
    print("Odds processing complete.")

def run_odds_processing(rounds=5):
    print("Starting odds processing simulation...")
    for _ in range(rounds):
        process_odds()
        time.sleep(1)  # Wait a bit between rounds
    print("Simulation complete.")


