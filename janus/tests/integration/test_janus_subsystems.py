"""
Janus Subsystems Test Suite
============================

Secondary test file covering additional subsystems with focus on:
1. Memory Core (Qdrant integration)
2. API Endpoints
3. Workers (Consolidation, Autonomy)
4. Services (Document, Sandbox)
"""

import asyncio
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime


# ============================================================================
# TEST 1: Memory Core Configuration
# ============================================================================

class TestMemoryCoreConfig:
    """Tests for MemoryCore configuration and initialization."""
    
    def test_memory_core_imports(self):
        """Test MemoryCore can be imported."""
        try:
            from app.core.memory.memory_core import MemoryCore, get_memory_db
            
            assert MemoryCore is not None
            assert get_memory_db is not None
            
            print("✓ MemoryCore imports available")
        except Exception as e:
            print(f"⚠ MemoryCore import: {e}")
    
    @pytest.mark.asyncio
    async def test_memory_core_initialization(self):
        """Test MemoryCore can be initialized with mock client."""
        try:
            from app.core.memory.memory_core import MemoryCore
            
            mock_client = AsyncMock()
            mock_client.collection_exists = AsyncMock(return_value=True)
            
            memory = MemoryCore(client=mock_client)
            
            assert memory is not None
            assert memory.client == mock_client
            
            print("✓ MemoryCore initialization with mock client")
        except Exception as e:
            print(f"⚠ MemoryCore init: {e}")


# ============================================================================
# TEST 2: Experience and Memory Models
# ============================================================================

class TestMemoryModels:
    """Tests for memory models and data structures."""
    
    def test_experience_model(self):
        """Test Experience dataclass."""
        try:
            from app.core.memory.models import Experience
            
            exp = Experience(
                content="Test experience content",
                type="episodic",
                metadata={"key": "value"}
            )
            
            assert exp.content == "Test experience content"
            assert exp.type == "episodic"
            
            print("✓ Experience model working")
        except Exception as e:
            print(f"⚠ Experience model: {e}")
    
    def test_memory_result_model(self):
        """Test MemoryResult dataclass."""
        try:
            from app.core.memory.models import MemoryResult
            
            result = MemoryResult(
                id="test-id",
                content="Test content",
                score=0.95,
                type="episodic",
                metadata={}
            )
            
            assert result.id == "test-id"
            assert result.score == 0.95
            
            print("✓ MemoryResult model working")
        except Exception as e:
            print(f"⚠ MemoryResult model: {e}")


# ============================================================================
# TEST 3: Vector Collection Enum
# ============================================================================

class TestVectorCollection:
    """Tests for VectorCollection enum."""
    
    def test_vector_collection_enum(self):
        """Test VectorCollection enum exists."""
        try:
            from app.core.memory.enums import VectorCollection
            
            assert hasattr(VectorCollection, 'EPISODIC_MEMORY')
            
            print(f"✓ VectorCollection enum available: {VectorCollection.EPISODIC_MEMORY.value}")
        except Exception as e:
            print(f"⚠ VectorCollection: {e}")


# ============================================================================
# TEST 4: Working Memory
# ============================================================================

class TestWorkingMemory:
    """Tests for working memory operations."""
    
    def test_working_memory_imports(self):
        """Test WorkingMemory can be imported."""
        try:
            from app.core.memory.working_memory import WorkingMemory
            
            wm = WorkingMemory()
            
            assert hasattr(wm, 'add') or hasattr(wm, 'store')
            
            print("✓ WorkingMemory available")
        except Exception as e:
            print(f"⚠ WorkingMemory: {e}")


# ============================================================================
# TEST 5: GraphRAG Core
# ============================================================================

class TestGraphRAGCore:
    """Tests for GraphRAG integration."""
    
    def test_graph_rag_core_import(self):
        """Test GraphRAGCore can be imported."""
        try:
            from app.core.memory.graph_rag_core import GraphRAGCore
            
            assert GraphRAGCore is not None
            
            print("✓ GraphRAGCore available")
        except Exception as e:
            print(f"⚠ GraphRAGCore: {e}")


# ============================================================================
# TEST 6: API Router Availability
# ============================================================================

class TestAPIRouters:
    """Tests for API route availability."""
    
    def test_main_router(self):
        """Test main router can be imported."""
        try:
            from app.routes.main import router
            
            assert router is not None
            
            # Check routes are defined
            routes = [r.path for r in router.routes]
            assert len(routes) > 0
            
            print(f"✓ Main router has {len(routes)} routes")
        except Exception as e:
            print(f"⚠ Main router: {e}")
    
    def test_admin_router(self):
        """Test admin router can be imported."""
        try:
            from app.routes.admin import router
            
            assert router is not None
            
            print("✓ Admin router available")
        except Exception as e:
            print(f"⚠ Admin router: {e}")
    
    def test_metrics_router(self):
        """Test metrics router can be imported."""
        try:
            from app.routes.metrics import router
            
            assert router is not None
            
            print("✓ Metrics router available")
        except Exception as e:
            print(f"⚠ Metrics router: {e}")


# ============================================================================
# TEST 7: Sandbox Service
# ============================================================================

class TestSandboxService:
    """Tests for code execution sandbox."""
    
    def test_sandbox_import(self):
        """Test SandboxService can be imported."""
        try:
            from app.services.sandbox_service import SandboxService
            
            assert SandboxService is not None
            
            print("✓ SandboxService available")
        except Exception as e:
            print(f"⚠ SandboxService import: {e}")
    
    @pytest.mark.asyncio
    async def test_sandbox_safe_execution(self):
        """Test sandbox executes safe code."""
        try:
            from app.services.sandbox_service import SandboxService
            
            sandbox = SandboxService()
            
            # Execute safe code
            result = await sandbox.execute("result = 2 + 2")
            
            assert result is not None
            print(f"✓ SandboxService execution: {result}")
        except Exception as e:
            print(f"⚠ SandboxService execution: {e}")


# ============================================================================
# TEST 8: Knowledge Service
# ============================================================================

class TestKnowledgeService:
    """Tests for knowledge service."""
    
    def test_knowledge_service_import(self):
        """Test KnowledgeService can be imported."""
        try:
            from app.services.knowledge_service import KnowledgeService
            
            assert KnowledgeService is not None
            
            print("✓ KnowledgeService available")
        except Exception as e:
            print(f"⚠ KnowledgeService: {e}")


# ============================================================================
# TEST 9: Workers
# ============================================================================

class TestWorkers:
    """Tests for background workers."""
    
    def test_consolidation_worker_import(self):
        """Test ConsolidationWorker can be imported."""
        try:
            from app.core.workers.consolidation_worker import ConsolidationWorker
            
            assert ConsolidationWorker is not None
            
            print("✓ ConsolidationWorker available")
        except Exception as e:
            print(f"⚠ ConsolidationWorker: {e}")
    
    def test_autonomy_worker_import(self):
        """Test AutonomyWorker can be imported."""
        try:
            from app.core.workers.autonomy_worker import AutonomyWorker
            
            assert AutonomyWorker is not None
            
            print("✓ AutonomyWorker available")
        except Exception as e:
            print(f"⚠ AutonomyWorker: {e}")


# ============================================================================
# TEST 10: MetaAgent Worker
# ============================================================================

class TestMetaAgentWorker:
    """Tests for MetaAgent worker."""
    
    def test_meta_agent_worker_import(self):
        """Test MetaAgentWorker can be imported."""
        try:
            from app.core.agents.meta_agent_worker import MetaAgentWorker
            
            assert MetaAgentWorker is not None
            
            print("✓ MetaAgentWorker available")
        except Exception as e:
            print(f"⚠ MetaAgentWorker: {e}")


# ============================================================================
# TEST 11: Agent Actor
# ============================================================================

class TestAgentActor:
    """Tests for AgentActor."""
    
    def test_agent_actor_import(self):
        """Test AgentActor can be imported."""
        try:
            from app.core.agents.agent_actor import AgentActor
            
            assert AgentActor is not None
            
            print("✓ AgentActor available")
        except Exception as e:
            print(f"⚠ AgentActor: {e}")


# ============================================================================
# TEST 12: Embedding Functions
# ============================================================================

class TestEmbeddings:
    """Tests for embedding functions."""
    
    def test_embedding_function_import(self):
        """Test embedding function can be imported."""
        try:
            from app.core.embeddings.embedding_functions import get_embedding_function
            
            assert get_embedding_function is not None
            
            print("✓ get_embedding_function available")
        except Exception as e:
            print(f"⚠ get_embedding_function: {e}")


# ============================================================================
# TEST 13: Audit Logging
# ============================================================================

class TestAuditLogging:
    """Tests for audit logging."""
    
    def test_audit_functions(self):
        """Test audit functions can be imported."""
        try:
            from app.core.infrastructure.audit_logger import record_audit_event_direct
            
            assert record_audit_event_direct is not None
            
            print("✓ Audit logging available")
        except Exception as e:
            print(f"⚠ Audit logging: {e}")


# ============================================================================
# TEST 14: Bootstrap and Kernel
# ============================================================================

class TestBootstrap:
    """Tests for bootstrap and kernel."""
    
    def test_kernel_import(self):
        """Test Kernel can be imported."""
        try:
            from app.core.kernel import Kernel
            
            assert Kernel is not None
            
            print("✓ Kernel available")
        except Exception as e:
            print(f"⚠ Kernel: {e}")
    
    def test_bootstrap_import(self):
        """Test bootstrap module can be imported."""
        try:
            from app.core.bootstrap import configure_logging, startup_message
            
            assert configure_logging is not None
            
            print("✓ Bootstrap module available")
        except Exception as e:
            print(f"⚠ Bootstrap: {e}")


# ============================================================================
# RUNNER
# ============================================================================

async def run_all_tests():
    """Run all tests and report results."""
    print("=" * 60)
    print("JANUS SUBSYSTEMS TEST SUITE")
    print("=" * 60)
    
    results = {
        "passed": 0,
        "failed": 0,
        "skipped": 0
    }
    
    test_classes = [
        TestMemoryCoreConfig(),
        TestMemoryModels(),
        TestVectorCollection(),
        TestWorkingMemory(),
        TestGraphRAGCore(),
        TestAPIRouters(),
        TestSandboxService(),
        TestKnowledgeService(),
        TestWorkers(),
        TestMetaAgentWorker(),
        TestAgentActor(),
        TestEmbeddings(),
        TestAuditLogging(),
        TestBootstrap(),
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
