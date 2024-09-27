import aiohttp
import asyncio
import time

async def read_api_key():
    with open('apikeys.txt', 'r') as file:
        return file.read().strip()

async def fetch_events(session, sport):
    api_key = await read_api_key()
    base_url = 'https://api.the-odds-api.com/v4'
    url = f'{base_url}/sports/{sport}/events'
    
    params = {'apiKey': api_key}
    
    async with session.get(url, params=params) as response:
        if response.status == 200:
            print(f"Events fetched successfully for {sport}")
            return await response.json(), response.headers
        else:
            print(f"Error fetching events for {sport}: {response.status}")
            return None, None

async def fetch_event_odds(session, sport, event_id, markets, regions='us,au', odds_format='american'):
    api_key = await read_api_key()
    base_url = 'https://api.the-odds-api.com/v4'
    url = f'{base_url}/sports/{sport}/events/{event_id}/odds'
    
    params = {
        'apiKey': api_key,
        'regions': regions,
        'markets': ','.join(markets),
        'oddsFormat': odds_format
    }
    
    async with session.get(url, params=params) as response:
        if response.status == 200:
            print(f"Odds fetched successfully for event {event_id}")
            return await response.json(), response.headers
        else:
            print(f"Error fetching odds for event {event_id}: {response.status}")
            return None, None

def get_quota_usage(headers):
    return {
        'requests_used': headers.get('x-requests-used', 'N/A'),
        'requests_remaining': headers.get('x-requests-remaining', 'N/A'),
        'requests_last': headers.get('x-requests-last', 'N/A')
    }

async def process_event_odds(event, odds, desired_bookmakers, market):
    print(f"\nEvent: {event['home_team']} vs {event['away_team']}")
    print(f"Market: {market}")
    
    if not odds:
        print("Failed to fetch odds data.")
        return

    available_bookmakers = {bm['key']: bm for bm in odds.get('bookmakers', [])}
    
    # Check if all desired bookmakers are available
    if not all(bm in available_bookmakers for bm in desired_bookmakers):
        print("Not all desired bookmakers are available for this event/market. Skipping.")
        return

    market_data = {}
    for bm_key in desired_bookmakers:
        bookmaker = available_bookmakers[bm_key]
        bm_market = next((m for m in bookmaker.get('markets', []) if m['key'] == market), None)
        
        if not bm_market:
            print(f"Market {market} not available for {bookmaker['title']}. Skipping.")
            return

        market_data[bm_key] = bm_market

    # Here you can add your calculations for this event, using data from all desired bookmakers
    # calculate_odds(event, market_data, market)

    # Print the collected data
    for bm_key, bm_market in market_data.items():
        print(f"  Bookmaker: {available_bookmakers[bm_key]['title']}")
        print(f"    Last update: {bm_market['last_update']}")
        for outcome in bm_market.get('outcomes', []):
            print(f"      Player: {outcome['description']}")
            price_info = f"{outcome['name']}: {outcome['price']}"
            if 'point' in outcome:
                price_info += f" (Point: {outcome['point']})"
            print(f"        {price_info}")

async def main():
    sport = 'americanfootball_nfl'
    market_bookmaker_combinations = [
        ('player_assists', ['draftkings'])
    ]
    
    regions = 'us,eu'  # Adjust as needed
    max_concurrent_requests = 2  # Reduced from 5
    
    async with aiohttp.ClientSession() as session:
        events, events_headers = await fetch_events(session, sport)
        if not events:
            print("Failed to fetch events.")
            return

        semaphore = asyncio.Semaphore(max_concurrent_requests)
        
        async def process_event_for_combination(event, market, bookmakers):
            async with semaphore:
                start_time = time.time()
                odds, headers = await fetch_event_odds(session, sport, event['id'], [market], regions)
                end_time = time.time()
                print(f"Fetch time for {event['home_team']} vs {event['away_team']} ({market}): {end_time - start_time:.2f} seconds")
                await process_event_odds(event, odds, bookmakers, market)
                return headers

        tasks = [
            process_event_for_combination(event, market, bookmakers)
            for event in events
            for market, bookmakers in market_bookmaker_combinations
        ]
        
        last_headers = None
        try:
            for completed_task in asyncio.as_completed(tasks):
                headers = await completed_task
                if headers:
                    last_headers = headers
        except Exception as e:
            print(f"An error occurred: {e}")

        # Print final API usage information
        print("\nFinal API Usage Information:")
        if last_headers:
            usage = get_quota_usage(last_headers)
            print(f"Requests used: {usage['requests_used']}")
            print(f"Requests remaining: {usage['requests_remaining']}")
            print(f"Used in last request: {usage['requests_last']}")
        else:
            print("No API usage information available.")

if __name__ == '__main__':
    asyncio.run(main())



