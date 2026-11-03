"""Does slow work in the background. Run with `python -m costpilot.worker`."""

import asyncio
import contextlib
import signal
import time

import structlog

from costpilot.composition import build_job_runner, build_retention_service
from costpilot.shared.config import get_settings
from costpilot.shared.database import Database
from costpilot.shared.logging import configure_logging
from costpilot.shared.telemetry import configure_telemetry, instrument_database

logger = structlog.get_logger()


async def main() -> None:
    settings = get_settings()
    configure_logging(settings)
    database = Database(settings.app_database_url)
    if configure_telemetry(settings, "costpilot-worker"):
        instrument_database(database.engine)
    runner = build_job_runner(settings, database)
    retention = build_retention_service(settings, database)
    retention_every = settings.retention_interval_hours * 3600
    next_retention = time.monotonic()

    stopping = asyncio.Event()
    loop = asyncio.get_running_loop()
    for stop_signal in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(stop_signal, stopping.set)

    logger.info("worker_started")
    while not stopping.is_set():
        if time.monotonic() >= next_retention:
            next_retention = time.monotonic() + retention_every
            try:
                await retention.run()
            except Exception:
                # Clean-up can wait for the next turn. Bills must keep being processed.
                logger.exception("retention_failed")
        did_work = await runner.run_once()
        if not did_work:
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(stopping.wait(), settings.worker_poll_seconds)
    await database.close()
    logger.info("worker_stopped")


if __name__ == "__main__":
    asyncio.run(main())
