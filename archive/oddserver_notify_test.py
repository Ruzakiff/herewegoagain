import asyncio
import json
import logging
from typing import Dict, List, Any

from notifymvp import process_test_notification
from archive.discord_notifier import notifier

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class NotifierTestProcessor:
    async def fetch_and_process(self):
        result = await process_test_notification()
        return result

async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    logger.info("New client connected")
    processor = NotifierTestProcessor()

    while True:
        data = await reader.readline()
        if not data:
            break
        message = data.decode().strip()
        logger.info(f"Received command: {message}")
        if message == "TEST_NOTIFY":
            result = await processor.fetch_and_process()
            writer.write(json.dumps(result).encode() + b'\n')
            await writer.drain()
    writer.close()
    await writer.wait_closed()
    logger.info("Client disconnected")

async def main():
    logger.info("Starting Notifier Test Server")
    server = await asyncio.start_server(handle_client, '127.0.0.1', 8888)
    addr = server.sockets[0].getsockname()
    logger.info(f'Serving on {addr}')

    # Start the Discord bot
    discord_task = asyncio.create_task(notifier.start())

    async with server:
        await server.serve_forever()

if __name__ == '__main__':
    logger.info("Starting Notifier Test Server")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        raise