import aiohttp
import asyncio
import time
import logging
import random
import csv
from typing import Dict
import calculations
import statistics  # Add this import at the top of your file

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s',
                    filename='fetch_log.txt', filemode='w')
logger = logging.getLogger(__name__)

class AggressiveTokenBucket:
    def __init__(self, rate, capacity):
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity
        self.last_refill = time.time()

    async def consume(self):
        now = time.time()
        time_passed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + time_passed * self.rate)
        self.last_refill = now

        if self.tokens >= 1:
            self.tokens -= 1
            return True
        return False

async def fetch_with_retry(session, url, params, token_bucket, max_retries=5, initial_backoff=1):
    for attempt in range(max_retries):
        if await token_bucket.consume():
            try:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        return await response.json(), response.headers
                    elif response.status == 429:
                        logger.warning(f"Rate limit hit (attempt {attempt + 1}/{max_retries}). Retrying...")
                    else:
                        logger.error(f"Error: Status {response.status}")
                        return None, None
            except Exception as e:
                logger.error(f"Request failed (attempt {attempt + 1}/{max_retries}): {e}")
        
        if attempt < max_retries - 1:
            backoff = initial_backoff * (2 ** attempt) + random.uniform(0, 1)
            await asyncio.sleep(backoff)
    
    logger.error(f"Failed to fetch data after {max_retries} attempts")
    return None, None

async def read_api_key():
    with open('apikeys.txt', 'r') as file:
        return file.read().strip()

async def fetch_events(session, sport, token_bucket):
    api_key = await read_api_key()
    base_url = 'https://api.the-odds-api.com/v4'
    url = f'{base_url}/sports/{sport}/events'
    
    params = {'apiKey': api_key}
    
    if await token_bucket.consume():
        return await fetch_with_retry(session, url, params, token_bucket)
    else:
        logger.warning("Rate limit exceeded. Skipping request.")
        return None, None

async def fetch_event_odds(session, sport, event_id, markets, token_bucket, regions='us,au', odds_format='american'):
    api_key = await read_api_key()
    base_url = 'https://api.the-odds-api.com/v4'
    url = f'{base_url}/sports/{sport}/events/{event_id}/odds'
    
    params = {
        'apiKey': api_key,
        'regions': regions,
        'markets': ','.join(markets),
        'oddsFormat': odds_format
    }
    
    if await token_bucket.consume():
        return await fetch_with_retry(session, url, params, token_bucket)
    else:
        logger.warning("Rate limit exceeded. Skipping request.")
        return None, None

def get_quota_usage(headers):
    return {
        'requests_used': headers.get('x-requests-used', 'N/A'),
        'requests_remaining': headers.get('x-requests-remaining', 'N/A'),
        'requests_last': headers.get('x-requests-last', 'N/A')
    }

async def process_event_odds(event, odds, desired_bookmakers, market, principal_bookmaker, base_bookmaker, optional_principals):
    logger.info(f"\nEvent: {event['home_team']} vs {event['away_team']}")
    logger.info(f"Market: {market}")
    
    if not odds:
        logger.error("Failed to fetch odds data.")
        return

    available_bookmakers = {bm['key']: bm for bm in odds.get('bookmakers', [])}
    
    # Check if principal and base bookmakers are available
    if principal_bookmaker not in available_bookmakers or base_bookmaker not in available_bookmakers:
        logger.warning(f"Both '{principal_bookmaker}' and '{base_bookmaker}' must be available. Skipping.")
        return

    # Get the market data for principal and base bookmakers
    principal_bm = available_bookmakers[principal_bookmaker]
    base_bm = available_bookmakers[base_bookmaker]
    principal_market = next((m for m in principal_bm.get('markets', []) if m['key'] == market), None)
    base_market = next((m for m in base_bm.get('markets', []) if m['key'] == market), None)
    
    if not principal_market or not base_market:
        logger.warning(f"Market {market} not available for both {principal_bookmaker} and {base_bookmaker}. Skipping.")
        return

    # Check if principal bookmaker has both 'yes' and 'no' outcomes
    principal_outcomes = {outcome['name'].lower(): outcome for outcome in principal_market['outcomes']}
    
    if not {'yes', 'no'}.issubset(principal_outcomes.keys()):
        logger.warning(f"{principal_bookmaker} does not have both 'yes' and 'no' outcomes. Skipping.")
        return

    logger.info(f"{principal_bookmaker} has both 'yes' and 'no' outcomes.")

    # Get available optional principal bookmakers
    available_optional_principals = [bm for bm in optional_principals if bm in available_bookmakers]
    
    # Create a set of player descriptions for all bookmakers
    all_players = set(outcome['description'] for outcome in principal_market['outcomes'])
    all_players.update(outcome['description'] for outcome in base_market['outcomes'])
    for opt_bm in available_optional_principals:
        opt_market = next((m for m in available_bookmakers[opt_bm].get('markets', []) if m['key'] == market), None)
        if opt_market:
            all_players.update(outcome['description'] for outcome in opt_market['outcomes'])

    # Log outcomes for all players and perform calculations
    logger.info("Outcomes and calculations for all players:")
    for description in all_players:
        logger.info(f"  Player: {description}")
        
        # Log principal bookmaker outcomes
        principal_yes = next((o for o in principal_market['outcomes'] if o['description'] == description and o['name'].lower() == 'yes'), None)
        principal_no = next((o for o in principal_market['outcomes'] if o['description'] == description and o['name'].lower() == 'no'), None)
        principal_yes_info = f"Yes: {principal_yes['price']}" if principal_yes else "Yes: N/A"
        principal_no_info = f"No: {principal_no['price']}" if principal_no else "No: N/A"
        logger.info(f"    {principal_bookmaker}: {principal_yes_info}, {principal_no_info}")
        
        # Log base bookmaker outcome
        base_yes = next((o for o in base_market['outcomes'] if o['description'] == description and o['name'].lower() == 'yes'), None)
        base_yes_info = f"Yes: {base_yes['price']}" if base_yes else "Yes: N/A"
        logger.info(f"    {base_bookmaker}: {base_yes_info}")
        
        # Log optional principal bookmakers outcomes
        valid_optional_prices = []
        for opt_bm in available_optional_principals:
            opt_market = next((m for m in available_bookmakers[opt_bm].get('markets', []) if m['key'] == market), None)
            if opt_market:
                opt_yes = next((o for o in opt_market['outcomes'] if o['description'] == description and o['name'].lower() == 'yes'), None)
                opt_no = next((o for o in opt_market['outcomes'] if o['description'] == description and o['name'].lower() == 'no'), None)
                opt_yes_info = f"Yes: {opt_yes['price']}" if opt_yes else "Yes: N/A"
                opt_no_info = f"No: {opt_no['price']}" if opt_no else "No: N/A"
                logger.info(f"    {opt_bm}: {opt_yes_info}, {opt_no_info}")
                if opt_yes and opt_no:
                    valid_optional_prices.append((opt_yes['price'], opt_no['price']))
            else:
                logger.info(f"    {opt_bm}: Market not available")

        # Calculate sharp prices if possible
        if principal_yes and principal_no:
            all_yes_prices = [principal_yes['price']] + [price[0] for price in valid_optional_prices]
            all_no_prices = [principal_no['price']] + [price[1] for price in valid_optional_prices]
            
            sharp_yes = statistics.mean(all_yes_prices)
            sharp_no = statistics.mean(all_no_prices)
            
            logger.info(f"    Sharp prices: Yes: {sharp_yes:.2f}, No: {sharp_no:.2f}")
            
            if base_yes:
                # Calculate edge
                implied_prob_sharp = 1 / (1 + 10000 / abs(sharp_yes)) if sharp_yes < 0 else 1 / (1 + abs(sharp_yes) / 100)
                implied_prob_base = 1 / (1 + 10000 / abs(base_yes['price'])) if base_yes['price'] < 0 else 1 / (1 + abs(base_yes['price']) / 100)
                edge = (implied_prob_sharp - implied_prob_base) / implied_prob_sharp * 100
                
                logger.info(f"    Edge: {edge:.2f}%")

    # Here you can add any additional processing or calculations if needed

async def process_event_for_combination(session, sport, event, market, bookmakers, token_bucket, regions):
    max_retries = 5
    for attempt in range(max_retries):
        if await token_bucket.consume():
            start_time = time.time()
            odds, headers = await fetch_event_odds(session, sport, event['id'], [market], token_bucket, regions)
            end_time = time.time()
            logger.info(f"Fetch time for {event['home_team']} vs {event['away_team']} ({market}): {end_time - start_time:.2f} seconds")
            
            if odds is not None:
                await process_event_odds(event, odds, bookmakers, market)
                return headers
            elif attempt < max_retries - 1:
                backoff = 1 * (2 ** attempt) + random.uniform(0, 1)
                logger.warning(f"Retrying {event['home_team']} vs {event['away_team']} ({market}) in {backoff:.2f} seconds...")
                await asyncio.sleep(backoff)
            else:
                logger.error(f"Failed to fetch odds for {event['home_team']} vs {event['away_team']} ({market}) after {max_retries} attempts")
        else:
            logger.warning(f"Rate limit exceeded for {event['home_team']} vs {event['away_team']} ({market}). Retrying...")
            await asyncio.sleep(1)
    return None

async def fetch_event_data(session, sport, event, market, bookmakers, token_bucket, regions, principal_bookmaker, base_bookmaker, optional_principals):
    api_key = await read_api_key()
    base_url = 'https://api.the-odds-api.com/v4'
    url = f'{base_url}/sports/{sport}/events/{event["id"]}/odds'
    
    params = {
        'apiKey': api_key,
        'regions': regions,
        'markets': market,
        'oddsFormat': 'american'
    }
    
    odds, headers = await fetch_with_retry(session, url, params, token_bucket)
    
    if odds:
        await process_event_odds(event, odds, bookmakers, market, principal_bookmaker, base_bookmaker, optional_principals)
    
    return headers

async def load_bookmaker_regions() -> Dict[str, str]:
    bookmaker_regions = {}
    try:
        with open('bookmakers.txt', 'r') as file:
            csv_reader = csv.reader(file)
            for row in csv_reader:
                if row and not row[0].startswith('#'):
                    if len(row) == 2:
                        bookmaker, region = row
                        bookmaker_regions[bookmaker.strip()] = region.strip()
                    else:
                        logger.warning(f"Invalid row in bookmakers.txt: {','.join(row)}")
    except FileNotFoundError:
        logger.error("bookmakers.txt file not found.")
    except Exception as e:
        logger.error(f"Error reading bookmakers.txt: {e}")
    
    return bookmaker_regions

async def main():
    overall_start_time = time.time()
    sport = 'americanfootball_nfl'
    market_bookmaker_combinations = [
        ('player_anytime_td', ['fliff', 'tab']),
        ('player_last_td', ['fliff','tab'])
    ]
    
    principal_bookmaker = 'fliff'
    base_bookmaker = 'tab'
    optional_principals = ['pinnacle', 'espnbet']  # Add optional principal bookmakers here
    
    # Load BOOKMAKER_REGIONS from file
    BOOKMAKER_REGIONS = await load_bookmaker_regions()
    
    if not BOOKMAKER_REGIONS:
        logger.error("No valid bookmaker regions loaded. Check bookmakers.txt file.")
        return

    # Automatically determine required regions
    required_regions = set()
    for _, bookmakers in market_bookmaker_combinations:
        for bookmaker in bookmakers:
            if bookmaker in BOOKMAKER_REGIONS:
                required_regions.add(BOOKMAKER_REGIONS[bookmaker])
            else:
                logger.warning(f"Unknown region for bookmaker: {bookmaker}")
    
    if not required_regions:
        logger.error("No valid regions determined. Check bookmaker names and bookmakers.txt file.")
        return

    regions = ','.join(required_regions)
    logger.info(f"Using regions: {regions}")
    
    # Adjust these values based on your API limits
    rate = 10  # tokens per second
    capacity = 50  # maximum tokens
    token_bucket = AggressiveTokenBucket(rate, capacity)
    
    async with aiohttp.ClientSession() as session:
        api_key = await read_api_key()
        
        events_start_time = time.time()
        events, _ = await fetch_with_retry(
            session, 
            f'https://api.the-odds-api.com/v4/sports/{sport}/events', 
            {'apiKey': api_key}, 
            token_bucket
        )
        events_end_time = time.time()
        logger.info(f"Time to fetch events: {events_end_time - events_start_time:.2f} seconds")
        
        if not events:
            logger.error("Failed to fetch events.")
            return

        logger.info(f"Number of events fetched: {len(events)}")

        tasks = [
            asyncio.create_task(fetch_event_data(
                session, sport, event, market, bookmakers, token_bucket, regions, 
                principal_bookmaker, base_bookmaker, optional_principals
            ))
            for event in events
            for market, bookmakers in market_bookmaker_combinations
        ]
        
        last_headers = None
        completed_tasks = 0
        total_tasks = len(tasks)
        
        odds_start_time = time.time()
        try:
            for task in asyncio.as_completed(tasks):
                try:
                    headers = await task
                    completed_tasks += 1
                    if headers:
                        last_headers = headers
                    logger.info(f"Completed {completed_tasks}/{total_tasks} tasks")
                except Exception as e:
                    logger.error(f"Error processing task: {e}")
        except Exception as e:
            logger.error(f"An error occurred in main loop: {e}")
        odds_end_time = time.time()

        # Log final API usage information
        if last_headers:
            usage = get_quota_usage(last_headers)
            logger.info(f"Requests used: {usage['requests_used']}")
            logger.info(f"Requests remaining: {usage['requests_remaining']}")
        else:
            logger.warning("No API usage information available.")

    overall_end_time = time.time()
    logger.info(f"Time to fetch events: {events_end_time - events_start_time:.2f} seconds")
    logger.info(f"Time to fetch all odds: {odds_end_time - odds_start_time:.2f} seconds")
    logger.info(f"Total execution time: {overall_end_time - overall_start_time:.2f} seconds")

if __name__ == '__main__':
    asyncio.run(main())