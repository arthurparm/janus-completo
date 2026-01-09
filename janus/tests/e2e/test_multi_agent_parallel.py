from unittest.mock import AsyncMock, patch

import pytest

from app.core.agents.multi_agent_system import Task


# Mock to avoid real RabbitMQ connection during simple unit test if infrastructure is not ready
@pytest.fixture
def mock_broker():
    # Patch at the source because multi_agent_system does local import
    with patch("app.core.infrastructure.message_broker.get_broker", new_callable=AsyncMock) as mock:
        yield mock

@pytest.mark.asyncio
async def test_multi_agent_parallel_dispatch(mock_broker):
    # Avoid initializing the whole system to prevent circular imports during test collection
    # We test the class directly

    from app.core.agents.multi_agent_system import AgentRole, MultiAgentSystem

    mas = MultiAgentSystem()

    # 2. Create agent (mocks actor start to avoid background task issues in test)
    with patch("app.core.agents.agent_actor.AgentActor.start", new_callable=AsyncMock):
        coder = mas.create_agent(AgentRole.CODER)

    # 3. Create task
    task = Task(
        description="Write a simple Hello World in Python",
        assigned_to=coder.agent_id,
        metadata={"test": True}
    )
    mas.workspace.add_task(task)

    # 4. Dispatch
    # Mock broker publish to verify it was called
    broker_instance = AsyncMock()
    mock_broker.return_value = broker_instance

    await mas.dispatch_task(task)

    # 5. Verify publish called
    assert broker_instance.publish.called
    args = broker_instance.publish.call_args
    assert args[0][0] == f"janus.agent.{AgentRole.CODER.value}"

    print(f"Tarefa {task.id} despachada com sucesso.")
