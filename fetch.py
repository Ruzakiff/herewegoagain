import aiohttp
import asyncio
import os

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

async def main():
    sport = 'americanfootball_nfl'
    markets = ['h2h', 'spreads', 'totals']
    regions = 'us,au'
    max_concurrent_requests = 5  # Limit the number of concurrent requests
    
    async with aiohttp.ClientSession() as session:
        # Fetch events
        events, events_headers = await fetch_events(session, sport)
        if not events:
            print("Failed to fetch events.")
            return

        # Fetch odds for each event concurrently with a limit on the number of concurrent requests
        semaphore = asyncio.Semaphore(max_concurrent_requests)
        
        async def fetch_odds_with_semaphore(event):
            async with semaphore:
                return await fetch_event_odds(session, sport, event['id'], markets, regions)
        
        odds_tasks = [fetch_odds_with_semaphore(event) for event in events]
        odds_results = await asyncio.gather(*odds_tasks)

        # Print results
        for event, (odds, _) in zip(events, odds_results):
            print(f"\nEvent: {event['home_team']} vs {event['away_team']}")
            if odds:
                print("Odds data:")
                for bookmaker in odds.get('bookmakers', []):
                    print(f"  Bookmaker: {bookmaker['title']}")
                    # The 'region' key might not be present, so we'll use get() with a default value
                    print(f"  Region: {bookmaker.get('region', 'N/A')}")
                    for market in bookmaker.get('markets', []):
                        print(f"    Market: {market['key']}")
                        for outcome in market.get('outcomes', []):
                            print(f"      {outcome['name']}: {outcome['price']}")
            else:
                print("Failed to fetch odds data.")

        # Print usage information at the end
        print("\nAPI Usage Information:")
        if odds_results and odds_results[-1][1]:  # Use the headers from the last API call
            usage = get_quota_usage(odds_results[-1][1])
            print(f"Requests used: {usage['requests_used']}")
            print(f"Requests remaining: {usage['requests_remaining']}")
            print(f"Used in last request: {usage['requests_last']}")

if __name__ == '__main__':
    asyncio.run(main())

