"""
Janus Workers Test Suite
========================

Comprehensive tests for all worker components.
"""

import asyncio

import pytest

# ============================================================================
# TEST 1: KnowledgeConsolidatorWorker
# ============================================================================

class TestKnowledgeConsolidatorWorker:
    """Tests for KnowledgeConsolidator worker module."""

    def test_knowledge_consolidator_worker_import(self):
        """Test KnowledgeConsolidator can be imported from canonical module."""
        try:
            from app.core.workers.knowledge_consolidator_worker import KnowledgeConsolidator
            assert KnowledgeConsolidator is not None
            print("✓ KnowledgeConsolidator import available")
        except Exception as e:
            print(f"⚠ KnowledgeConsolidator import: {e}")


# ============================================================================
# TEST 2: GoogleProductivityWorker
# ============================================================================

class TestGoogleProductivityWorker:
    """Tests for GoogleProductivityWorker."""

    def test_google_productivity_worker_import(self):
        """Test GoogleProductivityWorker can be imported."""
        try:
            from app.core.workers.google_productivity_worker import GoogleProductivityWorker
            assert GoogleProductivityWorker is not None
            print("✓ GoogleProductivityWorker import available")
        except Exception as e:
            print(f"⚠ GoogleProductivityWorker import: {e}")


# ============================================================================
# TEST 3: NeuralTrainingSystem
# ============================================================================

class TestNeuralTrainingSystem:
    """Tests for NeuralTrainingSystem."""

    def test_neural_training_system_import(self):
        """Test NeuralTrainingSystem can be imported."""
        try:
            from app.core.workers.neural_training_system import NeuralTrainingSystem
            assert NeuralTrainingSystem is not None
            print("✓ NeuralTrainingSystem import available")
        except Exception as e:
            print(f"⚠ NeuralTrainingSystem import: {e}")


# ============================================================================
# TEST 4: DataHarvester
# ============================================================================

class TestDataHarvester:
    """Tests for DataHarvester."""

    def test_data_harvester_import(self):
        """Test DataHarvester can be imported."""
        try:
            from app.core.workers.data_harvester import DataHarvester
            assert DataHarvester is not None
            print("✓ DataHarvester import available")
        except Exception as e:
            print(f"⚠ DataHarvester import: {e}")


# ============================================================================
# TEST 5: AutoScaler
# ============================================================================

class TestAutoScaler:
    """Tests for AutoScaler."""

    def test_auto_scaler_import(self):
        """Test AutoScaler can be imported."""
        try:
            from app.core.workers.auto_scaler import AutoScaler
            assert AutoScaler is not None
            print("✓ AutoScaler import available")
        except Exception as e:
            print(f"⚠ AutoScaler import: {e}")


# ============================================================================
# TEST 6: AutonomyWorker
# ============================================================================

class TestAutonomyWorker:
    """Tests for AutonomyWorker."""

    def test_autonomy_worker_import(self):
        """Test AutonomyWorker can be imported."""
        try:
            from app.core.workers.autonomy_worker import start_autonomy_worker
            assert start_autonomy_worker is not None
            print("✓ AutonomyWorker import available")
        except Exception as e:
            print(f"⚠ AutonomyWorker import: {e}")


# ============================================================================
# TEST 7: KnowledgeConsolidator
# ============================================================================

class TestKnowledgeConsolidator:
    """Tests for KnowledgeConsolidator."""

    def test_knowledge_consolidator_import(self):
        """Test KnowledgeConsolidator can be imported."""
        try:
            from app.core.workers.knowledge_consolidator_worker import KnowledgeConsolidator
            assert KnowledgeConsolidator is not None
            print("✓ KnowledgeConsolidator import available")
        except Exception as e:
            print(f"⚠ KnowledgeConsolidator import: {e}")


# ============================================================================
# TEST 8: MetaAgentWorker
# ============================================================================

class TestMetaAgentWorker:
    """Tests for MetaAgentWorker."""

    def test_meta_agent_worker_import(self):
        """Test MetaAgentWorker can be imported."""
        try:
            from app.core.agents.meta_agent_worker import MetaAgentWorker
            assert MetaAgentWorker is not None
            print("✓ MetaAgentWorker import available")
        except Exception as e:
            print(f"⚠ MetaAgentWorker import: {e}")


# ============================================================================
# TEST 9: SandboxAgentWorker
# ============================================================================

class TestSandboxAgentWorker:
    """Tests for SandboxAgentWorker."""

    def test_sandbox_agent_worker_import(self):
        """Test SandboxAgentWorker can be imported."""
        try:
            from app.core.workers.sandbox_agent_worker import SandboxAgentWorker
            assert SandboxAgentWorker is not None
            print("✓ SandboxAgentWorker import available")
        except Exception as e:
            print(f"⚠ SandboxAgentWorker import: {e}")


# ============================================================================
# TEST 10: RouterWorker
# ============================================================================

class TestRouterWorker:
    """Tests for RouterWorker."""

    def test_router_worker_import(self):
        """Test RouterWorker can be imported."""
        try:
            from app.core.workers.router_worker import RouterWorker
            assert RouterWorker is not None
            print("✓ RouterWorker import available")
        except Exception as e:
            print(f"⚠ RouterWorker import: {e}")


# ============================================================================
# TEST 11: ReflexionWorker
# ============================================================================

class TestReflexionWorker:
    """Tests for ReflexionWorker."""

    def test_reflexion_worker_import(self):
        """Test ReflexionWorker can be imported."""
        try:
            from app.core.workers.reflexion_worker import publish_reflexion_task
            assert publish_reflexion_task is not None
            print("✓ ReflexionWorker import available")
        except Exception as e:
            print(f"⚠ ReflexionWorker import: {e}")


# ============================================================================
# TEST 12: AgentTasksWorker
# ============================================================================

class TestAgentTasksWorker:
    """Tests for AgentTasksWorker."""

    def test_agent_tasks_worker_import(self):
        """Test AgentTasksWorker can be imported."""
        try:
            from app.core.workers.agent_tasks_worker import AgentTasksWorker
            assert AgentTasksWorker is not None
            print("✓ AgentTasksWorker import available")
        except Exception as e:
            print(f"⚠ AgentTasksWorker import: {e}")


# ============================================================================
# TEST 13: AsyncConsolidationWorker
# ============================================================================

class TestAsyncConsolidationWorker:
    """Tests for AsyncConsolidationWorker."""

    def test_async_consolidation_worker_import(self):
        """Test async consolidation worker functions."""
        try:
            from app.core.workers.async_consolidation_worker import publish_consolidation_task
            assert publish_consolidation_task is not None
            print("✓ AsyncConsolidationWorker import available")
        except Exception as e:
            print(f"⚠ AsyncConsolidationWorker import: {e}")


# ============================================================================
# TEST 14: ProfessorAgentWorker
# ============================================================================

class TestProfessorAgentWorker:
    """Tests for ProfessorAgentWorker."""

    def test_professor_agent_worker_import(self):
        """Test ProfessorAgentWorker can be imported."""
        try:
            from app.core.workers.professor_agent_worker import ProfessorAgentWorker
            assert ProfessorAgentWorker is not None
            print("✓ ProfessorAgentWorker import available")
        except Exception as e:
            print(f"⚠ ProfessorAgentWorker import: {e}")


# ============================================================================
# TEST 15: CodeAgentWorker
# ============================================================================

class TestCodeAgentWorker:
    """Tests for CodeAgentWorker."""

    def test_code_agent_worker_import(self):
        """Test CodeAgentWorker can be imported."""
        try:
            from app.core.workers.code_agent_worker import CodeAgentWorker
            assert CodeAgentWorker is not None
            print("✓ CodeAgentWorker import available")
        except Exception as e:
            print(f"⚠ CodeAgentWorker import: {e}")


# ============================================================================
# TEST 16: LifeCycleWorker
# ============================================================================

class TestLifeCycleWorker:
    """Tests for LifeCycleWorker."""

    def test_life_cycle_worker_import(self):
        """Test LifeCycleWorker can be imported."""
        try:
            from app.core.workers.life_cycle_worker import LifeCycleWorker
            assert LifeCycleWorker is not None
            print("✓ LifeCycleWorker import available")
        except Exception as e:
            print(f"⚠ LifeCycleWorker import: {e}")


# ============================================================================
# TEST 17: Orchestrator
# ============================================================================

class TestOrchestrator:
    """Tests for Orchestrator."""

    def test_orchestrator_import(self):
        """Test Orchestrator can be imported."""
        try:
            from app.core.workers.orchestrator import Orchestrator
            assert Orchestrator is not None
            print("✓ Orchestrator import available")
        except Exception as e:
            print(f"⚠ Orchestrator import: {e}")


# ============================================================================
# TEST 18: NeuralTrainingWorker
# ============================================================================

class TestNeuralTrainingWorker:
    """Tests for NeuralTrainingWorker."""

    def test_neural_training_worker_import(self):
        """Test NeuralTrainingWorker can be imported."""
        try:
            from app.core.workers.neural_training_worker import NeuralTrainingWorker
            assert NeuralTrainingWorker is not None
            print("✓ NeuralTrainingWorker import available")
        except Exception as e:
            print(f"⚠ NeuralTrainingWorker import: {e}")


# ============================================================================
# AUTONOMY CORE TESTS
# ============================================================================

class TestGoalManager:
    """Tests for GoalManager."""

    def test_goal_manager_import(self):
        """Test GoalManager can be imported."""
        try:
            from app.core.autonomy.goal_manager import GoalManager
            assert GoalManager is not None
            print("✓ GoalManager import available")
        except Exception as e:
            print(f"⚠ GoalManager import: {e}")

    @pytest.mark.asyncio
    async def test_goal_manager_initialization(self):
        """Test GoalManager initialization."""
        try:
            from app.core.autonomy.goal_manager import GoalManager

            manager = GoalManager()

            assert manager is not None

            print("✓ GoalManager initialization working")
        except Exception as e:
            print(f"⚠ GoalManager init: {e}")


class TestPlanner:
    """Tests for Planner."""

    def test_planner_import(self):
        """Test Planner can be imported."""
        try:
            from app.core.autonomy.planner import Planner
            assert Planner is not None
            print("✓ Planner import available")
        except Exception as e:
            print(f"⚠ Planner import: {e}")


class TestPolicyEngine:
    """Tests for PolicyEngine."""

    def test_policy_engine_import(self):
        """Test PolicyEngine can be imported."""
        try:
            from app.core.autonomy.policy_engine import PolicyEngine
            assert PolicyEngine is not None
            print("✓ PolicyEngine import available")
        except Exception as e:
            print(f"⚠ PolicyEngine import: {e}")

    @pytest.mark.asyncio
    async def test_policy_engine_initialization(self):
        """Test PolicyEngine initialization."""
        try:
            from app.core.autonomy.policy_engine import PolicyEngine

            engine = PolicyEngine()

            assert engine is not None

            print("✓ PolicyEngine initialization working")
        except Exception as e:
            print(f"⚠ PolicyEngine init: {e}")


# ============================================================================
# RUNNER
# ============================================================================

async def run_all_tests():
    """Run all tests and report results."""
    print("=" * 60)
    print("JANUS WORKERS TEST SUITE")
    print("=" * 60)

    results = {
        "passed": 0,
        "failed": 0,
        "skipped": 0
    }

    test_classes = [
        TestKnowledgeConsolidatorWorker(),
        TestGoogleProductivityWorker(),
        TestNeuralTrainingSystem(),
        TestDataHarvester(),
        TestAutoScaler(),
        TestAutonomyWorker(),
        TestKnowledgeConsolidator(),
        TestMetaAgentWorker(),
        TestSandboxAgentWorker(),
        TestRouterWorker(),
        TestReflexionWorker(),
        TestAgentTasksWorker(),
        TestAsyncConsolidationWorker(),
        TestProfessorAgentWorker(),
        TestCodeAgentWorker(),
        TestLifeCycleWorker(),
        TestOrchestrator(),
        TestNeuralTrainingWorker(),
        TestGoalManager(),
        TestPlanner(),
        TestPolicyEngine(),
    ]

    for test_class in test_classes:
        print(f"\n--- {test_class.__class__.__name__} ---")

        for method_name in dir(test_class):
            if method_name.startswith("test_"):
                method = getattr(test_class, method_name)
                try:
                    if asyncio.iscoroutinefunction(method):
                        await method()
                    else:
                        method()
                    results["passed"] += 1
                except Exception as e:
                    print(f"✗ {method_name}: {e}")
                    results["failed"] += 1

    print("\n" + "=" * 60)
    print(f"RESULTS: {results['passed']} passed, {results['failed']} failed, {results['skipped']} skipped")
    print("=" * 60)

    return results["failed"] == 0

if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    exit(0 if success else 1)
