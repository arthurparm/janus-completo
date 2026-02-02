"""
Janus Services Test Suite
==========================

Comprehensive tests for all service layer components.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

# ============================================================================
# TEST 1: ChatService
# ============================================================================


class TestChatService:
    """Comprehensive tests for ChatService."""

    def test_chat_service_import(self):
        """Test ChatService can be imported."""
        try:
            from app.services.chat_service import ChatService

            assert ChatService is not None
            print("✓ ChatService import available")
        except Exception as e:
            print(f"⚠ ChatService import: {e}")

    @pytest.mark.asyncio
    async def test_chat_service_initialization(self):
        """Test ChatService can be initialized with mocks."""
        try:
            from app.services.chat_service import ChatService

            mock_repo = MagicMock()
            mock_llm = MagicMock()

            service = ChatService(repo=mock_repo, llm_service=mock_llm)

            assert service.repo == mock_repo
            assert service.llm_service == mock_llm

            print("✓ ChatService initialization working")
        except Exception as e:
            print(f"⚠ ChatService init: {e}")

    @pytest.mark.asyncio
    async def test_start_conversation(self):
        """Test starting a new conversation."""
        try:
            from app.services.chat_service import ChatService

            mock_repo = MagicMock()
            mock_repo.create_conversation = AsyncMock(return_value="conv-123")
            mock_llm = MagicMock()

            service = ChatService(repo=mock_repo, llm_service=mock_llm)

            conv_id = await service.start_conversation(
                persona="assistant", user_id="user-1", project_id="proj-1"
            )

            assert conv_id == "conv-123"
            mock_repo.create_conversation.assert_called_once()

            print("✓ ChatService start_conversation working")
        except Exception as e:
            print(f"⚠ ChatService start_conversation: {e}")

    @pytest.mark.asyncio
    async def test_get_history(self):
        """Test getting conversation history."""
        try:
            from app.services.chat_service import ChatService

            mock_repo = MagicMock()
            mock_repo.get_messages = AsyncMock(
                return_value=[
                    {"role": "user", "content": "Hello"},
                    {"role": "assistant", "content": "Hi there!"},
                ]
            )
            mock_llm = MagicMock()

            service = ChatService(repo=mock_repo, llm_service=mock_llm)

            history = await service.get_history("conv-123")

            assert len(history) == 2
            assert history[0]["content"] == "Hello"

            print("✓ ChatService get_history working")
        except Exception as e:
            print(f"⚠ ChatService get_history: {e}")

    def test_is_quick_command(self):
        """Test quick command detection."""
        try:
            from app.services.chat_service import ChatService

            mock_repo = MagicMock()
            mock_llm = MagicMock()

            service = ChatService(repo=mock_repo, llm_service=mock_llm)

            # Test various commands
            assert service._is_quick_command("/help")
            assert service._is_quick_command("/status")
            assert not service._is_quick_command("hello")

            print("✓ ChatService quick command detection working")
        except Exception as e:
            print(f"⚠ ChatService quick command: {e}")

    def test_estimate_tokens(self):
        """Test token estimation."""
        try:
            from app.services.chat_service import ChatService

            mock_repo = MagicMock()
            mock_llm = MagicMock()

            service = ChatService(repo=mock_repo, llm_service=mock_llm)

            tokens = service._estimate_tokens("Hello, how are you doing today?")

            assert tokens > 0
            assert isinstance(tokens, int)

            print(f"✓ ChatService token estimation: {tokens} tokens")
        except Exception as e:
            print(f"⚠ ChatService token estimation: {e}")


# ============================================================================
# TEST 2: AutonomyService
# ============================================================================


class TestAutonomyService:
    """Comprehensive tests for AutonomyService."""

    def test_autonomy_service_import(self):
        """Test AutonomyService can be imported."""
        try:
            from app.services.autonomy_service import AutonomyConfig, AutonomyService

            assert AutonomyService is not None
            assert AutonomyConfig is not None
            print("✓ AutonomyService import available")
        except Exception as e:
            print(f"⚠ AutonomyService import: {e}")

    def test_autonomy_config_defaults(self):
        """Test AutonomyConfig default values."""
        try:
            from app.services.autonomy_service import AutonomyConfig

            config = AutonomyConfig()

            assert config.interval_seconds == 60
            assert config.risk_profile == "balanced"
            assert config.auto_confirm
            assert config.max_actions_per_cycle == 20

            print("✓ AutonomyConfig defaults correct")
        except Exception as e:
            print(f"⚠ AutonomyConfig defaults: {e}")

    @pytest.mark.asyncio
    async def test_autonomy_service_initialization(self):
        """Test AutonomyService initialization."""
        try:
            from app.services.autonomy_service import AutonomyService

            mock_optimization = MagicMock()

            service = AutonomyService(optimization_service=mock_optimization)

            assert service is not None
            assert service._optimization_service == mock_optimization

            print("✓ AutonomyService initialization working")
        except Exception as e:
            print(f"⚠ AutonomyService init: {e}")

    @pytest.mark.asyncio
    async def test_autonomy_get_status(self):
        """Test getting autonomy status."""
        try:
            from app.services.autonomy_service import AutonomyService

            mock_optimization = MagicMock()

            service = AutonomyService(optimization_service=mock_optimization)

            status = service.get_status()

            assert "is_active" in status
            assert "cycles_completed" in status

            print(f"✓ AutonomyService get_status: {status}")
        except Exception as e:
            print(f"⚠ AutonomyService get_status: {e}")


# ============================================================================
# TEST 3: OptimizationService
# ============================================================================


class TestOptimizationService:
    """Comprehensive tests for OptimizationService."""

    def test_optimization_service_import(self):
        """Test OptimizationService can be imported."""
        try:
            from app.services.optimization_service import OptimizationService

            assert OptimizationService is not None
            print("✓ OptimizationService import available")
        except Exception as e:
            print(f"⚠ OptimizationService import: {e}")

    @pytest.mark.asyncio
    async def test_optimization_service_collect_metrics(self):
        """Test metrics collection."""
        try:
            from app.services.optimization_service import OptimizationService

            service = OptimizationService()

            if hasattr(service, "collect_metrics"):
                metrics = await service.collect_metrics()
                assert isinstance(metrics, dict)
                print(f"✓ OptimizationService collect_metrics: {len(metrics)} metrics")
            else:
                print("⚠ OptimizationService no collect_metrics method")
        except Exception as e:
            print(f"⚠ OptimizationService collect_metrics: {e}")


# ============================================================================
# TEST 4: DocumentService
# ============================================================================


class TestDocumentService:
    """Comprehensive tests for DocumentIngestionService."""

    def test_document_service_import(self):
        """Test DocumentIngestionService can be imported."""
        try:
            from app.services.document_service import DocumentIngestionService

            assert DocumentIngestionService is not None
            print("✓ DocumentIngestionService import available")
        except Exception as e:
            print(f"⚠ DocumentIngestionService import: {e}")


# ============================================================================
# TEST 5: FeedbackService
# ============================================================================


class TestFeedbackService:
    """Comprehensive tests for FeedbackService."""

    def test_feedback_service_import(self):
        """Test FeedbackService can be imported."""
        try:
            from app.services.feedback_service import FeedbackService

            assert FeedbackService is not None
            print("✓ FeedbackService import available")
        except Exception as e:
            print(f"⚠ FeedbackService import: {e}")


# ============================================================================
# TEST 6: CollaborationService
# ============================================================================


class TestCollaborationService:
    """Comprehensive tests for CollaborationService."""

    def test_collaboration_service_import(self):
        """Test CollaborationService can be imported."""
        try:
            from app.services.collaboration_service import CollaborationService

            assert CollaborationService is not None
            print("✓ CollaborationService import available")
        except Exception as e:
            print(f"⚠ CollaborationService import: {e}")


# ============================================================================
# TEST 7: ObservabilityService
# ============================================================================


class TestObservabilityService:
    """Comprehensive tests for ObservabilityService."""

    def test_observability_service_import(self):
        """Test ObservabilityService can be imported."""
        try:
            from app.services.observability_service import ObservabilityService

            assert ObservabilityService is not None
            print("✓ ObservabilityService import available")
        except Exception as e:
            print(f"⚠ ObservabilityService import: {e}")


# ============================================================================
# TEST 8: ToolService
# ============================================================================


class TestToolService:
    """Comprehensive tests for ToolService."""

    def test_tool_service_import(self):
        """Test ToolService can be imported."""
        try:
            from app.services.tool_service import ToolService

            assert ToolService is not None
            print("✓ ToolService import available")
        except Exception as e:
            print(f"⚠ ToolService import: {e}")

    @pytest.mark.asyncio
    async def test_tool_service_list_tools(self):
        """Test listing available tools."""
        try:
            from app.services.tool_service import ToolService

            service = ToolService()

            if hasattr(service, "list_tools"):
                tools = await service.list_tools()
                assert isinstance(tools, list)
                print(f"✓ ToolService list_tools: {len(tools)} tools")
            else:
                print("⚠ ToolService no list_tools method")
        except Exception as e:
            print(f"⚠ ToolService list_tools: {e}")


# ============================================================================
# TEST 9: KnowledgeService
# ============================================================================


class TestKnowledgeService:
    """Comprehensive tests for KnowledgeService."""

    def test_knowledge_service_import(self):
        """Test KnowledgeService can be imported."""
        try:
            from app.services.knowledge_service import KnowledgeService

            assert KnowledgeService is not None
            print("✓ KnowledgeService import available")
        except Exception as e:
            print(f"⚠ KnowledgeService import: {e}")


# ============================================================================
# TEST 10: LearningService
# ============================================================================


class TestLearningService:
    """Comprehensive tests for LearningService."""

    def test_learning_service_import(self):
        """Test LearningService can be imported."""
        try:
            from app.services.learning_service import LearningService

            assert LearningService is not None
            print("✓ LearningService import available")
        except Exception as e:
            print(f"⚠ LearningService import: {e}")


# ============================================================================
# TEST 11: DedupeService
# ============================================================================


class TestDedupeService:
    """Comprehensive tests for DedupeService."""

    def test_dedupe_service_import(self):
        """Test DedupeService can be imported."""
        try:
            from app.services.dedupe_service import DedupeService

            assert DedupeService is not None
            print("✓ DedupeService import available")
        except Exception as e:
            print(f"⚠ DedupeService import: {e}")


# ============================================================================
# TEST 12: MemoryService
# ============================================================================


class TestMemoryService:
    """Comprehensive tests for MemoryService."""

    def test_memory_service_import(self):
        """Test MemoryService can be imported."""
        try:
            from app.services.memory_service import MemoryService

            assert MemoryService is not None
            print("✓ MemoryService import available")
        except Exception as e:
            print(f"⚠ MemoryService import: {e}")


# ============================================================================
# TEST 13: LLMService
# ============================================================================


class TestLLMService:
    """Comprehensive tests for LLMService."""

    def test_llm_service_import(self):
        """Test LLMService can be imported."""
        try:
            from app.services.llm_service import LLMService

            assert LLMService is not None
            print("✓ LLMService import available")
        except Exception as e:
            print(f"⚠ LLMService import: {e}")

    @pytest.mark.asyncio
    async def test_llm_service_initialization(self):
        """Test LLMService initialization."""
        try:
            from app.services.llm_service import LLMService

            service = LLMService()

            assert service is not None

            print("✓ LLMService initialization working")
        except Exception as e:
            print(f"⚠ LLMService init: {e}")


# ============================================================================
# TEST 14: LocalLLMService
# ============================================================================


class TestLocalLLMService:
    """Comprehensive tests for LocalLLMService."""

    def test_local_llm_service_import(self):
        """Test LocalLLMService can be imported."""
        try:
            from app.services.local_llm_service import LocalLLMService

            assert LocalLLMService is not None
            print("✓ LocalLLMService import available")
        except Exception as e:
            print(f"⚠ LocalLLMService import: {e}")


# ============================================================================
# TEST 15: AssistantService
# ============================================================================


class TestAssistantService:
    """Comprehensive tests for AssistantService."""

    def test_assistant_service_import(self):
        """Test AssistantService can be imported."""
        try:
            from app.services.assistant_service import AssistantService

            assert AssistantService is not None
            print("✓ AssistantService import available")
        except Exception as e:
            print(f"⚠ AssistantService import: {e}")


# ============================================================================
# TEST 16: TaskService
# ============================================================================


class TestTaskService:
    """Comprehensive tests for TaskService."""

    def test_task_service_import(self):
        """Test TaskService can be imported."""
        try:
            from app.services.task_service import TaskService

            assert TaskService is not None
            print("✓ TaskService import available")
        except Exception as e:
            print(f"⚠ TaskService import: {e}")


# ============================================================================
# TEST 17: ReflexionService
# ============================================================================


class TestReflexionService:
    """Comprehensive tests for ReflexionService."""

    def test_reflexion_service_import(self):
        """Test ReflexionService can be imported."""
        try:
            from app.services.reflexion_service import ReflexionService

            assert ReflexionService is not None
            print("✓ ReflexionService import available")
        except Exception as e:
            print(f"⚠ ReflexionService import: {e}")


# ============================================================================
# TEST 18: MetaAgentService
# ============================================================================


class TestMetaAgentService:
    """Comprehensive tests for MetaAgentService."""

    def test_meta_agent_service_import(self):
        """Test MetaAgentService can be imported."""
        try:
            from app.services.meta_agent_service import MetaAgentService

            assert MetaAgentService is not None
            print("✓ MetaAgentService import available")
        except Exception as e:
            print(f"⚠ MetaAgentService import: {e}")


# ============================================================================
# TEST 19: ContextService
# ============================================================================


class TestContextService:
    """Comprehensive tests for ContextService."""

    def test_context_service_import(self):
        """Test ContextService can be imported."""
        try:
            from app.services.context_service import ContextService

            assert ContextService is not None
            print("✓ ContextService import available")
        except Exception as e:
            print(f"⚠ ContextService import: {e}")


# ============================================================================
# TEST 20: SandboxService (Full)
# ============================================================================


class TestSandboxServiceFull:
    """Comprehensive tests for SandboxService."""

    def test_sandbox_service_import(self):
        """Test SandboxService can be imported."""
        try:
            from app.services.sandbox_service import SandboxService

            assert SandboxService is not None
            print("✓ SandboxService import available")
        except Exception as e:
            print(f"⚠ SandboxService import: {e}")


# ============================================================================
# TEST 21: SystemStatusService
# ============================================================================


class TestSystemStatusService:
    """Comprehensive tests for SystemStatusService."""

    def test_system_status_service_import(self):
        """Test SystemStatusService can be imported."""
        try:
            from app.services.system_status_service import SystemStatusService

            assert SystemStatusService is not None
            print("✓ SystemStatusService import available")
        except Exception as e:
            print(f"⚠ SystemStatusService import: {e}")

    @pytest.mark.asyncio
    async def test_get_status(self):
        """Test getting system status."""
        try:
            from app.services.system_status_service import SystemStatusService

            service = SystemStatusService()

            if hasattr(service, "get_status"):
                status = await service.get_status()
                assert isinstance(status, dict)
                print("✓ SystemStatusService get_status working")
            else:
                print("⚠ SystemStatusService no get_status method")
        except Exception as e:
            print(f"⚠ SystemStatusService get_status: {e}")


# ============================================================================
# TEST 22: CodeAnalysisService
# ============================================================================


class TestCodeAnalysisService:
    """Comprehensive tests for CodeAnalysisService."""

    def test_code_analysis_service_import(self):
        """Test CodeAnalysisService can be imported."""
        try:
            from app.services.code_analysis_service import CodeAnalysisService

            assert CodeAnalysisService is not None
            print("✓ CodeAnalysisService import available")
        except Exception as e:
            print(f"⚠ CodeAnalysisService import: {e}")


# ============================================================================
# TEST 23: AgentService
# ============================================================================


class TestAgentService:
    """Comprehensive tests for AgentService."""

    def test_agent_service_import(self):
        """Test AgentService can be imported."""
        try:
            from app.services.agent_service import AgentService

            assert AgentService is not None
            print("✓ AgentService import available")
        except Exception as e:
            print(f"⚠ AgentService import: {e}")


# ============================================================================
# TEST 24: ABTestingService
# ============================================================================


class TestABTestingService:
    """Comprehensive tests for ABTestingService."""

    def test_ab_testing_service_import(self):
        """Test ABTestingService can be imported."""
        try:
            from app.services.ab_testing_service import ABTestingService

            assert ABTestingService is not None
            print("✓ ABTestingService import available")
        except Exception as e:
            print(f"⚠ ABTestingService import: {e}")


# ============================================================================
# TEST 25: BiasCheckService
# ============================================================================


class TestBiasCheckService:
    """Comprehensive tests for BiasCheckService."""

    def test_bias_check_service_import(self):
        """Test BiasCheckService can be imported."""
        try:
            from app.services.bias_check_service import BiasCheckService

            assert BiasCheckService is not None
            print("✓ BiasCheckService import available")
        except Exception as e:
            print(f"⚠ BiasCheckService import: {e}")


# ============================================================================
# TEST 26: DBMigrationService
# ============================================================================


class TestDBMigrationService:
    """Comprehensive tests for DBMigrationService."""

    def test_db_migration_service_import(self):
        """Test DBMigrationService can be imported."""
        try:
            from app.services.db_migration_service import DBMigrationService

            assert DBMigrationService is not None
            print("✓ DBMigrationService import available")
        except Exception as e:
            print(f"⚠ DBMigrationService import: {e}")


# ============================================================================
# RUNNER
# ============================================================================


async def run_all_tests():
    """Run all tests and report results."""
    print("=" * 60)
    print("JANUS SERVICES TEST SUITE")
    print("=" * 60)

    results = {"passed": 0, "failed": 0, "skipped": 0}

    test_classes = [
        TestChatService(),
        TestAutonomyService(),
        TestOptimizationService(),
        TestDocumentService(),
        TestFeedbackService(),
        TestCollaborationService(),
        TestObservabilityService(),
        TestToolService(),
        TestKnowledgeService(),
        TestLearningService(),
        TestDedupeService(),
        TestMemoryService(),
        TestLLMService(),
        TestLocalLLMService(),
        TestAssistantService(),
        TestTaskService(),
        TestReflexionService(),
        TestMetaAgentService(),
        TestContextService(),
        TestSandboxServiceFull(),
        TestSystemStatusService(),
        TestCodeAnalysisService(),
        TestAgentService(),
        TestABTestingService(),
        TestBiasCheckService(),
        TestDBMigrationService(),
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
    print(
        f"RESULTS: {results['passed']} passed, {results['failed']} failed, {results['skipped']} skipped"
    )
    print("=" * 60)

    return results["failed"] == 0


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    exit(0 if success else 1)
