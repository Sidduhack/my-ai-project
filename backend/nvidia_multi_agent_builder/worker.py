"""Entry point for Render background worker - runs the scheduler."""

import asyncio
import signal
import sys
from nvidia_multi_agent_builder.config.settings import Settings
from nvidia_multi_agent_builder.db import init_engine
from nvidia_multi_agent_builder.orchestration import Orchestrator
from nvidia_multi_agent_builder.config.logging import configure_logging, get_logger

logger = get_logger(__name__)


async def main():
    """Run the orchestrator/scheduler as a background worker."""
    configure_logging(log_level="INFO", log_format="json")
    
    # Load settings from environment
    settings = Settings()
    
    # Initialize database engine
    init_engine(settings.database_url)
    
    # Create orchestrator
    orchestrator = Orchestrator(
        max_concurrent_tasks=10,
        max_concurrent_per_agent=3,
    )
    
    # Setup signal handlers for graceful shutdown
    shutdown_event = asyncio.Event()
    
    def signal_handler(signum, frame):
        logger.info("Shutdown signal received", signum=signum)
        shutdown_event.set()
    
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        logger.info("Starting orchestrator worker")
        await orchestrator.start()
        
        # Wait for shutdown signal
        await shutdown_event.wait()
        
    except Exception as e:
        logger.error("Worker error", error=str(e))
        raise
    finally:
        logger.info("Stopping orchestrator worker")
        await orchestrator.stop()
        logger.info("Worker stopped")


if __name__ == "__main__":
    asyncio.run(main())