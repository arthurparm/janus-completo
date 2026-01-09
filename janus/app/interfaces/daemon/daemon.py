import asyncio

import structlog

from app.core.kernel import Kernel
from app.core.monitoring.watchdog import Watchdog

logger = structlog.get_logger(__name__)


async def main():
    """
    Main entry point for the Janus Daemon.
    Starts the Core Kernel and waits for shutdown signals.
    """
    kernel = Kernel.get_instance()

    # Initialize Watchdog
    watchdog = Watchdog.get_instance()
    watchdog.register_component("daemon_main", timeout_seconds=120.0)  # leniency for startup
    watchdog.start()

    # Handle Shutdown Signals
    stop_event = asyncio.Event()

    def signal_handler(sig, frame):
        logger.info(f"Received shutdown signal {sig}")
        stop_event.set()
        watchdog.stop()

    # Register signal handlers if not on Windows completely or handle differently?
    # Windows doesn't support SIGUSR1 etc, but supports SIGINT/SIGTERM
    # signal.signal(signal.SIGINT, signal_handler) # asyncio handles this better often

    restart_count = 0
    MAX_RESTARTS_FAST = 5
    RESET_TIME = 60  # seconds to reset restart count

    while not stop_event.is_set():
        watchdog.beat("daemon_main")  # Beat at start of outer restart loop
        start_time = asyncio.get_event_loop().time()
        try:
            logger.info("Starting Janus Daemon (Jarvis Mode)...")
            await kernel.startup()
            logger.info("Daemon is running. Press Ctrl+C to stop.")

            # Main Operational Loop
            while not stop_event.is_set():
                watchdog.beat("daemon_main")  # Beat every loop
                # 1. Voice Interaction (If enabled)
                if kernel.voice_manager and kernel.voice_manager._enabled:
                    try:
                        # Non-blocking check? wait_for_wake_word is blocking in logic potentially?
                        # wait_for_wake_word should handle short blocks or be designed to run continuously.
                        # Implementation of wakeword was 'loop running chunks'. It returns True if found.
                        # We might needed to ensure it yields control or runs in executor (it does).

                        # Optimization: Only listen if not processing something else?
                        # For now, simplistic sequential flow.
                        if await kernel.voice_manager.wait_for_wake_word():
                            logger.info("Wake Word Detected! Listening for command...")
                            # Play 'Listening' sound? (Future)

                            command = await kernel.voice_manager.listen()
                            if command:
                                logger.info(f"Command received: {command}")
                                # TODO: Send to ChatService/LLM
                                # response = await kernel.chat_service.process(command)
                                # For now, simple echo/placeholder
                                response = f"Entendido: {command}"
                                await kernel.voice_manager.speak(response)
                            else:
                                logger.info("No command heard.")
                    except Exception as e:
                        logger.error(f"Error in Voice Loop: {e}", exc_info=False)
                        # Cool-down to prevent log spam if mic is broken
                        await asyncio.sleep(5)

                # 2. Other Core Loops (Monitoring, etc handled by background workers)
                await asyncio.sleep(0.1)

        except (KeyboardInterrupt, asyncio.CancelledError):
            logger.info("Shutdown requested by user.")
            stop_event.set()
            break
        except Exception as e:
            logger.critical(f"Daemon Critical Failure: {e}", exc_info=True)
            restart_count += 1

            # Logic to handle restarts
            run_duration = asyncio.get_event_loop().time() - start_time
            if run_duration > RESET_TIME:
                restart_count = 1  # Reset if it ran successfully for a while

            if restart_count > MAX_RESTARTS_FAST:
                logger.error("Too many crashes in short period. Sleeping 60s...")
                await asyncio.sleep(60)
                restart_count = 0  # Retry after long sleep
            else:
                await asyncio.sleep(restart_count * 2)  # Exponential-ish backoff
        finally:
            logger.info("Cleaning up before potential restart/shutdown...")
            try:
                await kernel.shutdown()
            except Exception as e:
                logger.error(f"Error during shutdown: {e}")

            if stop_event.is_set():
                logger.info("Daemon stopped.")
                break
            else:
                logger.info("Restarting Daemon...")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
