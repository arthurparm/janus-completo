import asyncio
import json
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime

from app.core.agents.meta_agent import MetaAgent, StateReport, DetectedIssue, Recommendation, IssueSeverity, IssueCategory
from app.core.agents.multi_agent_system import MultiAgentSystem, AgentRole, TaskStatus

# --- Mocks ---

class MockBroker:
    def __init__(self):
        self.published_messages = []

    async def connect(self):
        pass

    async def publish(self, queue_name, message, **kwargs):
        self.published_messages.append({"queue": queue_name, "message": message})
        
    def start_consumer(self, *args, **kwargs):
         # Mock consumer start
         return asyncio.create_task(asyncio.sleep(0))


@pytest.mark.asyncio
async def test_proactive_remediation_flow():
    # 1. Setup Mock Broker
    mock_broker = MockBroker()
    
    # 2. Patch dependencies
    with patch("app.core.infrastructure.message_broker.get_broker", new=AsyncMock(return_value=mock_broker)), \
         patch("app.core.agents.meta_agent.get_llm") as mock_get_llm, \
         patch("app.core.agents.multi_agent_system.get_llm", return_value=MagicMock()):

        # Mock LLM response to force a specific recommendation
        mock_llm_instance = MagicMock()
        mock_llm_instance.invoke.return_value = """
        {
          "overall_status": "critical",
          "health_score": 45,
          "issues": [
            {
              "severity": "critical",
              "category": "resource",
              "title": "Disk Space Critical",
              "description": "Root partition is 98% full",
              "evidence": {"disk_usage": "98%"}
            }
          ],
          "recommendations": [
            {
              "category": "resource",
              "title": "Clean Temporary Files",
              "description": "Remove files in /tmp older than 7 days",
              "rationale": "Free up space to prevent system crash",
              "priority": 5,
              "suggested_agent": "sysadmin"
            }
          ],
          "summary": "Critical disk space issue detected."
        }
        """
        mock_get_llm.return_value = mock_llm_instance

        # 3. Initialize Systems
        # We need to init MAS first so it registers itself as the singleton if applicable, 
        # or we patch get_multi_agent_system if MetaAgent uses it.
        # MetaAgent imports get_multi_agent_system inside _auto_remediate.
        
        # Initialize MAS and SysAdmin
        mas = MultiAgentSystem()
        # Ensure SysAdmin is created (Kernel does this usually, but we do it manually here)
        mas.create_agent(AgentRole.SYSADMIN)
        
        # Patch get_multi_agent_system used by MetaAgent
        with patch("app.core.agents.multi_agent_system.get_multi_agent_system", return_value=mas), \
             patch("app.core.agents.meta_agent.analyze_memory_for_failures") as mock_mem, \
             patch("app.core.agents.meta_agent.get_system_health_metrics") as mock_health, \
             patch("app.core.agents.meta_agent.analyze_performance_trends") as mock_perf, \
             patch("app.core.agents.meta_agent.get_resource_usage") as mock_res:
            
            mock_mem.invoke.return_value = "{}"
            mock_health.invoke.return_value = "{}"
            mock_perf.invoke.return_value = "{}"
            mock_res.invoke.return_value = "{}"
            
            # 4. Initialize MetaAgent
            meta_agent = MetaAgent()
            
            # 5. Run Analysis Cycle
            print("Running Analysis Cycle...")
            report = await meta_agent.run_analysis_cycle()
            
            # 6. Assertions
            
            # Check Report Content
            assert report.overall_status == "critical"
            assert len(report.recommendations) == 1
            assert report.recommendations[0].suggested_agent == "sysadmin"
            
            # Check Task Creation in Workspace
            tasks = mas.workspace.get_tasks_by_status(TaskStatus.PENDING)
            assert len(tasks) > 0
            task = tasks[0]
            print(f"Task Created: {task.description} assigned to {task.assigned_to}")
            
            assert "[AUTO-REMEDIATION]" in task.description
            assert "Clean Temporary Files" in task.description
            
            # Verify Agent Assignment
            sysadmin_agent = mas.agents[task.assigned_to]
            assert sysadmin_agent.role == AgentRole.SYSADMIN
            
            # Check Message Dispatch
            assert len(mock_broker.published_messages) == 1
            msg = mock_broker.published_messages[0]
            assert msg["queue"] == f"janus.agent.sysadmin"
            
            payload = msg["message"]
            # Message is a Pydantic model dump or dict?
            # Broker receives TaskMessage model dump usually, verify wrapper.
            # In dispatch_task: await broker.publish(queue, msg.model_dump())
            
            assert payload["task_id"] == task.id
            assert payload["task_type"] == "agent_task"
            print("Verified: Task dispatched to Broker queue 'janus.agent.sysadmin'")

if __name__ == "__main__":
    # Allow running directly
    asyncio.run(test_proactive_remediation_flow())
    print("Test Passed!")
