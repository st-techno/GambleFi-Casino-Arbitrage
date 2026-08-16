"""
Enterprise Application Bootstrapper.
"""
import asyncio
import logging
import sys
from core.bot import ArbitrageBot

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] [%(filename)s:%(lineno)d] -> %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("MainEntry")

async def main():
    """Initializes and runs the core system orchestration loops cleanly."""
    try:
        bot = ArbitrageBot()
        await bot.run_forever()
    except KeyboardInterrupt:
        logger.info("Operational shutdown command parsed via keystroke handler. Turning down system arrays.")
    except Exception as e:
        logger.critical(f"Fatal platform execution termination encounter: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
