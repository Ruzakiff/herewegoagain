import asyncio
import aiohttp
from typing import Dict, Any, AsyncGenerator

class Config:
    def __init__(self):
        self.base_url = "https://api.the-odds-api.com/v4"
        self.api_key = "1cc1fb33251e9c1c1a25fb1c88c0a7ab"  # Your API key
        self.rate_limit = 10  # Requests per second
        self.max_retries = 3

class Cache:
    # Simple in-memory cache implementation
    def __init__(self):
        self.cache = {}

    def get(self, key):
        return self.cache.get(key)

    def set(self, key, value):
        self.cache[key] = value

class RateLimiter:
    def __init__(self, rate_limit):
        self.rate_limit = rate_limit
        self.tokens = rate_limit
        self.last_update = asyncio.get_event_loop().time()

    async def wait(self):
        now = asyncio.get_event_loop().time()
        time_passed = now - self.last_update
        self.tokens = min(self.rate_limit, self.tokens + time_passed * self.rate_limit)
        
        if self.tokens < 1:
            await asyncio.sleep((1 - self.tokens) / self.rate_limit)
            self.tokens = 1
        
        self.tokens -= 1
        self.last_update = now

class OddsAPIClient:
    def __init__(self, config: Config):
        self.config = config
        self.session = aiohttp.ClientSession()
        self.cache = Cache()
        self.rate_limiter = RateLimiter(config.rate_limit)

    async def fetch_events(self, **params) -> AsyncGenerator[Dict[str, Any], None]:
        url = f"{self.config.base_url}/sports/{params.get('sport', 'upcoming')}/events"
        async for result in self._fetch_with_retry(url, params):
            yield result

    async def fetch_odds(self, **params) -> AsyncGenerator[Dict[str, Any], None]:
        url = f"{self.config.base_url}/sports/{params.get('sport', 'upcoming')}/odds"
        async for result in self._fetch_with_retry(url, params):
            yield result

    async def _fetch_with_retry(self, url: str, params: Dict[str, Any]) -> AsyncGenerator[Dict[str, Any], None]:
        retries = self.config.max_retries
        while retries > 0:
            try:
                await self.rate_limiter.wait()
                params['apiKey'] = self.config.api_key
                if 'regions' not in params:
                    params['regions'] = 'us'  # Add default region if not provided
                async with self.session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        if isinstance(data, list):
                            for item in data:
                                yield item
                        else:
                            yield data
                    else:
                        error_text = await response.text()
                        print(f"Error {response.status}: {error_text}")
                        yield None
                break
            except aiohttp.ClientError as e:
                print(f"Error: {e}")
                retries -= 1
                if retries == 0:
                    raise
                await asyncio.sleep(2 ** (self.config.max_retries - retries))

    async def close(self):
        await self.session.close()

async def main():
    config = Config()
    client = OddsAPIClient(config)
    
    async def process_events():
        async for event in client.fetch_events(sport='upcoming'):
            if event:
                print(f"Received event: {event.get('id', 'Unknown')}")
            # Process event
    
    async def process_odds():
        async for odds in client.fetch_odds(sport='upcoming', markets='h2h'):
            if odds:
                print(f"Received odds: {odds.get('id', 'Unknown')}")
            # Process odds

    await asyncio.gather(process_events(), process_odds())
    await client.close()

if __name__ == '__main__':
    asyncio.run(main())