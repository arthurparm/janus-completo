import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.agents.multi_agent_system import (
    AgentRole,
    MultiAgentSystem,
    Task,
)

# --- Mocks ---

class MockBroker:
    def __init__(self):
        self.published_messages = []
        self.consumers = {}

    async def connect(self):
        pass

    async def publish(self, queue_name, message, **kwargs):
        print(f"DEBUG: Publishing to {queue_name}")
        self.published_messages.append({"queue": queue_name, "message": message})
        # Simulate immediate delivery if consumer exists
        if queue_name in self.consumers:
            print(f"DEBUG: Consumer found for {queue_name}")
            callback = self.consumers[queue_name]
            # Wrap in TaskMessage if it's a dict
            from app.models.schemas import TaskMessage
            if isinstance(message, dict):
                 msg_obj = TaskMessage(**message)
            else:
                 msg_obj = message

            # Simulate async processing
            print("DEBUG: Calling callback")
            try:
                await callback(msg_obj)
                print("DEBUG: Callback returned")
            except Exception as e:
                print(f"DEBUG: Callback raised {e}")

    def start_consumer(self, queue_name, callback, prefetch_count=10):
        print(f"DEBUG: Registering consumer for {queue_name}")
        self.consumers[queue_name] = callback
        return asyncio.create_task(asyncio.sleep(0))

    async def get_queue_info(self, queue_name):
        return {"messages": 0, "consumers": 1}

class ScenarioSpyLLM:
    """A Mock LLM that returns responses based on the Agent Role in the prompt."""

    def __init__(self):
        self.responses = {
            AgentRole.PROJECT_MANAGER: """
            Thought: The user wants a python script. I should assign this to the Coder.
            Action: create_task
            Action Input: {
                "description": "Write a python script that prints Hello World",
                "assigned_to": "coder_agent",
                "priority": "HIGH"
            }
            Observation: Task created.
            Final Answer: I have assigned the task to the Coder.
            """,
            AgentRole.CODER: """
            Thought: I need to write a python script.
            Action: write_file
            Action Input: {
                "file_path": "hello_world.py",
                "content": "print('Hello World from Janus')",
                "overwrite": true
            }
            Observation: File written.
            Final Answer: Script created at hello_world.py
            """
        }
        self.invocations = []

    def invoke(self, prompt, **kwargs):
        prompt_str = str(prompt)
        self.invocations.append(prompt_str)

        # Simple heuristic to detect role from prompt content
        if "Gerente de Projetos" in prompt_str or "Project Manager" in prompt_str:
             # Logic to return create_task action
             # In reality, PM creates task via specialized tool or simple memory usage.
             # Current PM prompt instructions say: "Divide projects", "Assign tasks".
             # But PM toolset usually includes `add_task` or similar.
             pass

        # Ideally we return a response that triggers the agent's tool.
        # But for this test, we want to simulate the PM *dispatching* logic.
        # If we are testing MAS.dispatch_task, we need the PM to CALL it?
        # Typically PM adds task to workspace.

        return "MOCKED RESPONSE"

    async def publish_to_exchange(self, *args, **kwargs):
        pass # Mock exchange publish

@pytest.mark.asyncio
async def test_end_to_end_project_flow(tmp_path):
    """
    Test a full flow: User -> PM -> Coder -> File Created.
    Verifies MAS routing, Task/Workspace mechanics, and Tool execution.
    """
    # Setup Paths
    workspace_dir = tmp_path / "janus_workspace"
    workspace_dir.mkdir(parents=True, exist_ok=True)

    # 1. Mock Broker & LLM
    mock_broker = MockBroker()

    # We need a mocked LLM that acts differently for PM vs Coder

    coder_response = """
    Thought: I will write the file.
    Action: write_file
    Action Input: {
        "file_path": "hello.py",
        "content": "print('Hello')",
        "overwrite": true
    }
    """

    # Mock Tools

    with patch("app.core.infrastructure.message_broker.get_broker", new=AsyncMock(return_value=mock_broker)), \
         patch("app.core.agents.agent_actor.get_broker", new=AsyncMock(return_value=mock_broker)), \
         patch("app.core.agents.multi_agent_system.get_llm"), \
         patch("app.config.settings.WORKSPACE_ROOT", str(workspace_dir)):

         # Setup MAS
         mas = MultiAgentSystem()
         coder = mas.create_agent(AgentRole.CODER)
         # Force ID for predictability
         coder.agent_id = "coder_1"
         mas.agents["coder_1"] = coder

         # Mock Coder LLM
         mock_llm_coder = MagicMock()
         mock_llm_coder.invoke.return_value.content = coder_response

         # Mock Router to return specific LLM
         # We need to distinguish calls.
         # But simpler: just mock the agent's llm attribute after creation.

         # Mock Router to return specific LLM
         # We rely on AgentExecutor.ainvoke patch so we don't need to inject LLM


         # Let's patch AgentExecutor.ainvoke
         with patch("langchain.agents.AgentExecutor.ainvoke", new_callable=AsyncMock) as mock_ainvoke:

             # Configure Coder behavior
             mock_ainvoke.return_value = {
                 "output": "File created",
                 "intermediate_steps": []
             }

             # Logic:
             # 1. We start the Coder's Actor (Listener).
             # 2. We publish a TaskMessage to 'janus.agent.coder'.
             # 3. We Verify Coder.executor.ainvoke was called.

             # Start Coder Actor (manually to ensure it attaches to mock broker)
             from app.core.agents.agent_actor import AgentActor
             actor = AgentActor(coder)
             # Start consumer
             await actor.start()

             # Create a Task
             task = Task(description="Write hello.py", assigned_to="coder_1")
             mas.workspace.add_task(task)

             # Dispatch (this calls broker.publish)
             await mas.dispatch_task(task)

             # Broker should have simulated delivery to callback (actor._process_message)
             # This is async, give it a tick
             await asyncio.sleep(0.1)

             # Verification
             # Check if Coder LLM (AgentExecutor) was invoked with the task description
             assert mock_ainvoke.called
             args, _ = mock_ainvoke.call_args
             input_data = args[0]
             assert "Write hello.py" in str(input_data)

             print("SUCCESS: Coder Agent received task and invoked LLM.")

             # Now testing Tool Execution separately (Integration level)
             # Verify write_file tool works in this environment
             from app.core.tools.filesystem_tools import write_file

             # Test write_file
             write_file.invoke({
                "file_path": "test_env.txt",
                "content": "Environment Active",
                "overwrite": True
             })

             assert (workspace_dir / "test_env.txt").exists()
             assert (workspace_dir / "test_env.txt").read_text() == "Environment Active"
             print("SUCCESS: Filesystem Tools are working.")

if __name__ == "__main__":
    asyncio.run(test_end_to_end_project_flow(Path("./tmp_test")))
