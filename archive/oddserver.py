import asyncio
import json
import logging
from typing import Dict, List, Any
import aiohttp

print("Starting import from fetch3")
from fetch3 import (
    AggressiveTokenBucket,
    fetch_events,
    fetch_event_data,
    read_api_key,
    load_bookmaker_regions
)
print("Finished import from fetch3")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

print("Defining OddsProcessor class")
class OddsProcessor:
    def __init__(self):
        print("Initializing OddsProcessor")
        self.data: Dict[str, Any] = {}
        self.token_bucket = AggressiveTokenBucket(rate=10, capacity=50)
        self.bookmaker_regions = {}
        self.api_key = None

    async def initialize(self):
        print("Initializing API key and bookmaker regions")
        self.api_key = await read_api_key()
        self.bookmaker_regions = await load_bookmaker_regions()

    async def fetch_and_process(self, sport: str, market_bookmaker_combinations: List[tuple], principal_bookmaker: str, base_bookmaker: str, optional_principals: List[str]):
        print("Starting fetch and process")
        async with aiohttp.ClientSession() as session:
            events, _ = await fetch_events(session, sport, self.token_bucket)
            if not events:
                print("Failed to fetch events.")
                return None

            print(f"Fetched {len(events)} events")

            regions = self.get_regions([bm for _, bookmakers in market_bookmaker_combinations for bm in bookmakers])

            tasks = [
                asyncio.create_task(fetch_event_data(
                    session, sport, event, market, bookmakers, self.token_bucket, regions,
                    principal_bookmaker, base_bookmaker, optional_principals
                ))
                for event in events
                for market, bookmakers in market_bookmaker_combinations
            ]

            await asyncio.gather(*tasks)

        print("Finished fetch and process")
        return self.data

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
        ('player_anytime_td', ['fliff', 'tab', 'espnbet', 'pinnacle']),
        ('player_last_td', ['fliff', 'tab', 'espnbet', 'pinnacle'])
    ]
    principal_bookmaker = 'fliff'
    base_bookmaker = 'tab'
    optional_principals = ['pinnacle', 'espnbet']

    while True:
        data = await reader.readline()
        if not data:
            break
        message = data.decode().strip()
        print(f"Received command: {message}")
        if message == "FETCH":
            result = await processor.fetch_and_process(sport, market_bookmaker_combinations, principal_bookmaker, base_bookmaker, optional_principals)
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
