import os
import sys
import asyncio
import json
from pathlib import Path

# Ensure local RabbitMQ connection for host execution
os.environ.setdefault("RABBITMQ_HOST", "localhost")
os.environ.setdefault("RABBITMQ_PORT", "5672")
os.environ.setdefault("RABBITMQ_MANAGEMENT_PORT", "15672")
os.environ.setdefault("RABBITMQ_USER", "janus")
os.environ.setdefault("RABBITMQ_PASSWORD", "janus_pass")

# Ensure repo root is on PYTHONPATH (for app.* imports)
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.core.infrastructure.message_broker import MessageBroker

QUEUE = "janus.knowledge.consolidation"


async def main():
    broker = MessageBroker()

    # Publish once to ensure the queue gets declared with expected arguments
    await broker.publish(QUEUE, "test-message-script")

    before = await broker.validate_queue_policy(QUEUE)
    print("VALIDATION_BEFORE:", json.dumps(before, ensure_ascii=False))

    recon = await broker.reconcile_queue_policy(QUEUE)
    print("RECONCILE:", json.dumps(recon, ensure_ascii=False))

    after = await broker.validate_queue_policy(QUEUE)
    print("VALIDATION_AFTER:", json.dumps(after, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
