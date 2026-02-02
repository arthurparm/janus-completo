import asyncio
import logging

import aio_pika
import pytest

from app.core.infrastructure.message_broker import MessageBroker
from app.models.schemas import TaskMessage

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_dlx_poison_pill():
    """
    Verifica se uma 'poison pill' (mensagem que causa erro) é
    movida para a Dead Letter Queue (DLQ) em vez de loop infinito.
    """
    broker = MessageBroker()
    queue_name = "janus.test.poison"

    # 1. Connect and Setup
    await broker.connect()

    # Force queue deletion to start fresh
    await broker.delete_queue(queue_name)
    await broker.delete_queue("janus.dlq")

    # 2. Declare Queue with DLX
    async with broker._connection.channel() as channel:
        # Declare DLX/DLQ manually to be sure (though broker code does it now)
        dlx = await channel.declare_exchange(
            "janus.dlx", type=aio_pika.ExchangeType.FANOUT, durable=True
        )
        dlq = await channel.declare_queue("janus.dlq", durable=True)
        await dlq.bind(dlx, routing_key="#")

        # Declare Test Queue pointing to DLX
        args = {"x-dead-letter-exchange": "janus.dlx"}
        test_queue = await channel.declare_queue(queue_name, durable=True, arguments=args)

        # Purge to be clean
        await test_queue.purge()
        await dlq.purge()

    print(f"\n[SETUP] Queues ready: {queue_name} -> janus.dlx -> janus.dlq")

    # 3. Define a consumer that ALWAYS fails
    async def poison_consumer(task: TaskMessage):
        print(f"[CONSUMER] Received task: {task.task_id}")
        if task.task_id == "poison_pill":
            raise ValueError("I AM A POISON PILL!")
        print("[CONSUMER] Processed normal task")

    # 4. Start Consumer
    consumer_task = broker.start_consumer(queue_name, poison_consumer, prefetch_count=1)

    # 5. Publish Poison Pill
    poison_msg = TaskMessage(task_id="poison_pill", task_type="test", payload={"data": "killer"})
    await broker.publish(queue_name, poison_msg.model_dump())
    print("[PUBLISH] Poison pill sent")

    # 6. Wait for processing (allow time for nack -> dlq)
    await asyncio.sleep(2)

    # 7. Access DLQ to verify message presence
    async with broker._connection.channel() as channel:
        dlq = await channel.declare_queue("janus.dlq", durable=True)
        message_count = dlq.declaration_result.message_count

        print(f"[ASSERT] DLQ Message Count: {message_count}")
        assert message_count == 1, "DLQ should contain exactly 1 message (the poison pill)"

        # Consume to inspect
        msg = await dlq.get(fail=False)
        assert msg is not None
        print(f"[ASSERT] Message in DLQ: {msg.body}")
        # Verify headers showing why it died
        headers = msg.headers
        x_death = headers.get("x-death", [])
        if x_death:
            reason = x_death[0].get("reason")
            print(f"[info] Reason for death: {reason}")
            assert reason == "rejected", "Reason should be 'rejected' (nack with requeue=False)"

    # Cleanup
    consumer_task.cancel()
    await broker.close()
    print("[SUCCESS] Poison pill correctly moved to DLQ!")


if __name__ == "__main__":
    asyncio.run(test_dlx_poison_pill())
