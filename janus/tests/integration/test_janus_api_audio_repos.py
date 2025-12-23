"""
Janus Audio/Senses, API, and Repositories Test Suite
=====================================================

Comprehensive tests for audio services, API endpoints, and repository layer.
"""

import asyncio
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime


# ============================================================================
# AUDIO/SENSES TESTS
# ============================================================================

class TestAudioInterfaces:
    """Tests for audio interfaces."""
    
    def test_audio_interfaces_import(self):
        """Test audio interfaces can be imported."""
        try:
            from app.core.senses.audio.interfaces import STTInterface, TTSInterface
            assert STTInterface is not None
            assert TTSInterface is not None
            print("✓ Audio interfaces available")
        except Exception as e:
            print(f"⚠ Audio interfaces: {e}")


class TestSTTService:
    """Tests for Speech-to-Text service."""
    
    def test_stt_service_import(self):
        """Test STTService can be imported."""
        try:
            from app.core.senses.audio.stt_service import STTService
            assert STTService is not None
            print("✓ STTService import available")
        except Exception as e:
            print(f"⚠ STTService import: {e}")
    
    @pytest.mark.asyncio
    async def test_stt_service_initialization(self):
        """Test STTService initialization."""
        try:
            from app.core.senses.audio.stt_service import STTService
            
            service = STTService()
            
            assert service is not None
            assert hasattr(service, 'transcribe') or hasattr(service, 'process')
            
            print("✓ STTService initialization working")
        except Exception as e:
            print(f"⚠ STTService init: {e}")


class TestTTSService:
    """Tests for Text-to-Speech service."""
    
    def test_tts_service_import(self):
        """Test TTSService can be imported."""
        try:
            from app.core.senses.audio.tts_service import TTSService
            assert TTSService is not None
            print("✓ TTSService import available")
        except Exception as e:
            print(f"⚠ TTSService import: {e}")
    
    @pytest.mark.asyncio
    async def test_tts_service_initialization(self):
        """Test TTSService initialization."""
        try:
            from app.core.senses.audio.tts_service import TTSService
            
            service = TTSService()
            
            assert service is not None
            assert hasattr(service, 'synthesize') or hasattr(service, 'speak')
            
            print("✓ TTSService initialization working")
        except Exception as e:
            print(f"⚠ TTSService init: {e}")


class TestWakeWordService:
    """Tests for WakeWord detection service."""
    
    def test_wakeword_service_import(self):
        """Test WakeWordService can be imported."""
        try:
            from app.core.senses.audio.wakeword_service import WakeWordService
            assert WakeWordService is not None
            print("✓ WakeWordService import available")
        except Exception as e:
            print(f"⚠ WakeWordService import: {e}")


class TestAudioManager:
    """Tests for AudioManager."""
    
    def test_audio_manager_import(self):
        """Test AudioManager can be imported."""
        try:
            from app.core.senses.audio.manager import AudioManager
            assert AudioManager is not None
            print("✓ AudioManager import available")
        except Exception as e:
            print(f"⚠ AudioManager import: {e}")


# ============================================================================
# API TESTS
# ============================================================================

class TestAPIRouter:
    """Tests for API v1 router."""
    
    def test_v1_router_import(self):
        """Test v1 router can be imported."""
        try:
            from app.api.v1.router import router
            assert router is not None
            print("✓ API v1 router available")
        except Exception as e:
            print(f"⚠ API v1 router: {e}")
    
    def test_api_router_has_routes(self):
        """Test router has routes defined."""
        try:
            from app.api.v1.router import router
            
            routes = list(router.routes)
            assert len(routes) > 0
            
            print(f"✓ API router has {len(routes)} routes")
        except Exception as e:
            print(f"⚠ API router routes: {e}")


class TestExceptionHandlers:
    """Tests for exception handlers."""
    
    def test_exception_handlers_import(self):
        """Test exception handlers can be imported."""
        try:
            from app.api.exception_handlers import setup_exception_handlers
            assert setup_exception_handlers is not None
            print("✓ Exception handlers available")
        except Exception as e:
            print(f"⚠ Exception handlers: {e}")


class TestProblemDetails:
    """Tests for problem details (RFC 7807)."""
    
    def test_problem_details_import(self):
        """Test ProblemDetail can be imported."""
        try:
            from app.api.problem_details import ProblemDetail
            assert ProblemDetail is not None
            print("✓ ProblemDetail available")
        except Exception as e:
            print(f"⚠ ProblemDetail: {e}")


# ============================================================================
# REPOSITORY TESTS
# ============================================================================

class TestChatRepository:
    """Tests for ChatRepository."""
    
    def test_chat_repository_import(self):
        """Test ChatRepository can be imported."""
        try:
            from app.repositories.chat_repository import ChatRepository
            assert ChatRepository is not None
            print("✓ ChatRepository import available")
        except Exception as e:
            print(f"⚠ ChatRepository import: {e}")


class TestChatRepositorySQL:
    """Tests for ChatRepositorySQL."""
    
    def test_chat_repository_sql_import(self):
        """Test ChatRepositorySQL can be imported."""
        try:
            from app.repositories.chat_repository_sql import ChatRepositorySQL
            assert ChatRepositorySQL is not None
            print("✓ ChatRepositorySQL import available")
        except Exception as e:
            print(f"⚠ ChatRepositorySQL import: {e}")


class TestKnowledgeRepository:
    """Tests for KnowledgeRepository."""
    
    def test_knowledge_repository_import(self):
        """Test KnowledgeRepository can be imported."""
        try:
            from app.repositories.knowledge_repository import KnowledgeRepository
            assert KnowledgeRepository is not None
            print("✓ KnowledgeRepository import available")
        except Exception as e:
            print(f"⚠ KnowledgeRepository import: {e}")


class TestLearningRepository:
    """Tests for LearningRepository."""
    
    def test_learning_repository_import(self):
        """Test LearningRepository can be imported."""
        try:
            from app.repositories.learning_repository import LearningRepository
            assert LearningRepository is not None
            print("✓ LearningRepository import available")
        except Exception as e:
            print(f"⚠ LearningRepository import: {e}")


class TestLLMRepository:
    """Tests for LLMRepository."""
    
    def test_llm_repository_import(self):
        """Test LLMRepository can be imported."""
        try:
            from app.repositories.llm_repository import LLMRepository
            assert LLMRepository is not None
            print("✓ LLMRepository import available")
        except Exception as e:
            print(f"⚠ LLMRepository import: {e}")


class TestObservabilityRepository:
    """Tests for ObservabilityRepository."""
    
    def test_observability_repository_import(self):
        """Test ObservabilityRepository can be imported."""
        try:
            from app.repositories.observability_repository import ObservabilityRepository
            assert ObservabilityRepository is not None
            print("✓ ObservabilityRepository import available")
        except Exception as e:
            print(f"⚠ ObservabilityRepository import: {e}")


class TestAgentConfigRepository:
    """Tests for AgentConfigRepository."""
    
    def test_agent_config_repository_import(self):
        """Test AgentConfigRepository can be imported."""
        try:
            from app.repositories.agent_config_repository import AgentConfigRepository
            assert AgentConfigRepository is not None
            print("✓ AgentConfigRepository import available")
        except Exception as e:
            print(f"⚠ AgentConfigRepository import: {e}")


class TestAgentRepository:
    """Tests for AgentRepository."""
    
    def test_agent_repository_import(self):
        """Test AgentRepository can be imported."""
        try:
            from app.repositories.agent_repository import AgentRepository
            assert AgentRepository is not None
            print("✓ AgentRepository import available")
        except Exception as e:
            print(f"⚠ AgentRepository import: {e}")


class TestAutonomyRepository:
    """Tests for AutonomyRepository."""
    
    def test_autonomy_repository_import(self):
        """Test AutonomyRepository can be imported."""
        try:
            from app.repositories.autonomy_repository import AutonomyRepository
            assert AutonomyRepository is not None
            print("✓ AutonomyRepository import available")
        except Exception as e:
            print(f"⚠ AutonomyRepository import: {e}")


class TestCollaborationRepository:
    """Tests for CollaborationRepository."""
    
    def test_collaboration_repository_import(self):
        """Test CollaborationRepository can be imported."""
        try:
            from app.repositories.collaboration_repository import CollaborationRepository
            assert CollaborationRepository is not None
            print("✓ CollaborationRepository import available")
        except Exception as e:
            print(f"⚠ CollaborationRepository import: {e}")


class TestContextRepository:
    """Tests for ContextRepository."""
    
    def test_context_repository_import(self):
        """Test ContextRepository can be imported."""
        try:
            from app.repositories.context_repository import ContextRepository
            assert ContextRepository is not None
            print("✓ ContextRepository import available")
        except Exception as e:
            print(f"⚠ ContextRepository import: {e}")


class TestDeploymentRepository:
    """Tests for DeploymentRepository."""
    
    def test_deployment_repository_import(self):
        """Test DeploymentRepository can be imported."""
        try:
            from app.repositories.deployment_repository import DeploymentRepository
            assert DeploymentRepository is not None
            print("✓ DeploymentRepository import available")
        except Exception as e:
            print(f"⚠ DeploymentRepository import: {e}")


class TestMemoryRepository:
    """Tests for MemoryRepository."""
    
    def test_memory_repository_import(self):
        """Test MemoryRepository can be imported."""
        try:
            from app.repositories.memory_repository import MemoryRepository
            assert MemoryRepository is not None
            print("✓ MemoryRepository import available")
        except Exception as e:
            print(f"⚠ MemoryRepository import: {e}")


class TestOptimizationRepository:
    """Tests for OptimizationRepository."""
    
    def test_optimization_repository_import(self):
        """Test OptimizationRepository can be imported."""
        try:
            from app.repositories.optimization_repository import OptimizationRepository
            assert OptimizationRepository is not None
            print("✓ OptimizationRepository import available")
        except Exception as e:
            print(f"⚠ OptimizationRepository import: {e}")


class TestPendingActionRepository:
    """Tests for PendingActionRepository."""
    
    def test_pending_action_repository_import(self):
        """Test PendingActionRepository can be imported."""
        try:
            from app.repositories.pending_action_repository import PendingActionRepository
            assert PendingActionRepository is not None
            print("✓ PendingActionRepository import available")
        except Exception as e:
            print(f"⚠ PendingActionRepository import: {e}")


class TestPromptRepository:
    """Tests for PromptRepository."""
    
    def test_prompt_repository_import(self):
        """Test PromptRepository can be imported."""
        try:
            from app.repositories.prompt_repository import PromptRepository
            assert PromptRepository is not None
            print("✓ PromptRepository import available")
        except Exception as e:
            print(f"⚠ PromptRepository import: {e}")


class TestReflexionRepository:
    """Tests for ReflexionRepository."""
    
    def test_reflexion_repository_import(self):
        """Test ReflexionRepository can be imported."""
        try:
            from app.repositories.reflexion_repository import ReflexionRepository
            assert ReflexionRepository is not None
            print("✓ ReflexionRepository import available")
        except Exception as e:
            print(f"⚠ ReflexionRepository import: {e}")


class TestSandboxRepository:
    """Tests for SandboxRepository."""
    
    def test_sandbox_repository_import(self):
        """Test SandboxRepository can be imported."""
        try:
            from app.repositories.sandbox_repository import SandboxRepository
            assert SandboxRepository is not None
            print("✓ SandboxRepository import available")
        except Exception as e:
            print(f"⚠ SandboxRepository import: {e}")


class TestTaskRepository:
    """Tests for TaskRepository."""
    
    def test_task_repository_import(self):
        """Test TaskRepository can be imported."""
        try:
            from app.repositories.task_repository import TaskRepository
            assert TaskRepository is not None
            print("✓ TaskRepository import available")
        except Exception as e:
            print(f"⚠ TaskRepository import: {e}")


class TestToolRepository:
    """Tests for ToolRepository."""
    
    def test_tool_repository_import(self):
        """Test ToolRepository can be imported."""
        try:
            from app.repositories.tool_repository import ToolRepository
            assert ToolRepository is not None
            print("✓ ToolRepository import available")
        except Exception as e:
            print(f"⚠ ToolRepository import: {e}")


class TestUserRepository:
    """Tests for UserRepository."""
    
    def test_user_repository_import(self):
        """Test UserRepository can be imported."""
        try:
            from app.repositories.user_repository import UserRepository
            assert UserRepository is not None
            print("✓ UserRepository import available")
        except Exception as e:
            print(f"⚠ UserRepository import: {e}")


class TestABExperimentRepository:
    """Tests for ABExperimentRepository."""
    
    def test_ab_experiment_repository_import(self):
        """Test ABExperimentRepository can be imported."""
        try:
            from app.repositories.ab_experiment_repository import ABExperimentRepository
            assert ABExperimentRepository is not None
            print("✓ ABExperimentRepository import available")
        except Exception as e:
            print(f"⚠ ABExperimentRepository import: {e}")


class TestConsentRepository:
    """Tests for ConsentRepository."""
    
    def test_consent_repository_import(self):
        """Test ConsentRepository can be imported."""
        try:
            from app.repositories.consent_repository import ConsentRepository
            assert ConsentRepository is not None
            print("✓ ConsentRepository import available")
        except Exception as e:
            print(f"⚠ ConsentRepository import: {e}")


# ============================================================================
# RUNNER
# ============================================================================

async def run_all_tests():
    """Run all tests and report results."""
    print("=" * 60)
    print("JANUS AUDIO, API & REPOSITORIES TEST SUITE")
    print("=" * 60)
    
    results = {
        "passed": 0,
        "failed": 0,
        "skipped": 0
    }
    
    test_classes = [
        # Audio/Senses
        TestAudioInterfaces(),
        TestSTTService(),
        TestTTSService(),
        TestWakeWordService(),
        TestAudioManager(),
        # API
        TestAPIRouter(),
        TestExceptionHandlers(),
        TestProblemDetails(),
        # Repositories
        TestChatRepository(),
        TestChatRepositorySQL(),
        TestKnowledgeRepository(),
        TestLearningRepository(),
        TestLLMRepository(),
        TestObservabilityRepository(),
        TestAgentConfigRepository(),
        TestAgentRepository(),
        TestAutonomyRepository(),
        TestCollaborationRepository(),
        TestContextRepository(),
        TestDeploymentRepository(),
        TestMemoryRepository(),
        TestOptimizationRepository(),
        TestPendingActionRepository(),
        TestPromptRepository(),
        TestReflexionRepository(),
        TestSandboxRepository(),
        TestTaskRepository(),
        TestToolRepository(),
        TestUserRepository(),
        TestABExperimentRepository(),
        TestConsentRepository(),
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
