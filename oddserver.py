import asyncio
import json
import logging
from typing import Dict, List, Any
import aiohttp

print("Starting import from fetch2")
from fetch2 import (
    AggressiveTokenBucket,
    fetch_events,
    fetch_event_odds,
    fetch_with_retry,
    process_event_odds,
    read_api_key
)
print("Finished import from fetch2")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

print("Defining OddsProcessor class")
class OddsProcessor:
    def __init__(self):
        print("Initializing OddsProcessor")
        self.data: Dict[str, Any] = {}
        self.token_bucket = AggressiveTokenBucket(rate=10, capacity=50)
        self.bookmaker_regions = self.load_bookmaker_regions()
        self.api_key = None

    async def initialize(self):
        print("Initializing API key")
        self.api_key = await read_api_key()

    async def fetch_and_process(self, sport: str, market_bookmaker_combinations: List[tuple]):
        print("Starting fetch and process")
        async with aiohttp.ClientSession() as session:
            events, _ = await fetch_events(session, sport, self.token_bucket)
            if not events:
                print("Failed to fetch events.")
                return None

            print(f"Fetched {len(events)} events")

            for event in events:
                for market, bookmakers in market_bookmaker_combinations:
                    regions = self.get_regions(bookmakers)
                    odds, _ = await fetch_event_odds(session, sport, event['id'], [market], self.token_bucket, regions)
                    if odds:
                        await process_event_odds(event, odds, bookmakers, market)

        print("Finished fetch and process")
        return self.data

    def load_bookmaker_regions(self) -> Dict[str, str]:
        print("Loading bookmaker regions")
        bookmaker_regions = {}
        try:
            with open('bookmakers.txt', 'r') as file:
                for line in file:
                    if line.strip() and not line.startswith('#'):
                        bookmaker, region = line.strip().split(',')
                        bookmaker_regions[bookmaker.strip()] = region.strip()
        except Exception as e:
            print(f"Error loading bookmaker regions: {e}")
        return bookmaker_regions

    def get_regions(self, bookmakers: List[str]) -> str:
        regions = set(self.bookmaker_regions.get(bm, '') for bm in bookmakers)
        return ','.join(filter(None, regions))

print("Defining handle_client function")
async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    print("New client connected")
    processor = OddsProcessor()
    await processor.initialize()
    sport = 'americanfootball_nfl'
    market_bookmaker_combinations = [
        ('player_anytime_td', ['draftkings', 'fanduel']),
        ('player_last_td', ['tab', 'fanduel'])
    ]

    while True:
        data = await reader.readline()
        if not data:
            break
        message = data.decode().strip()
        print(f"Received command: {message}")
        if message == "FETCH":
            result = await processor.fetch_and_process(sport, market_bookmaker_combinations)
            writer.write(json.dumps(result).encode() + b'\n')
            await writer.drain()
    writer.close()
    await writer.wait_closed()
    print("Client disconnected")

print("Defining main function")
async def main():
    print("Starting server")
    server = await asyncio.start_server(handle_client, '127.0.0.1', 8888)
    addr = server.sockets[0].getsockname()
    print(f'Serving on {addr}')

    async with server:
        await server.serve_forever()

if __name__ == '__main__':
    print("Starting Odds Server")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Server stopped by user")
    except Exception as e:
        print(f"Failed to start server: {e}")
        raise
