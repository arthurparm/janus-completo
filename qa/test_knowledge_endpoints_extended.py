import pytest
from httpx import AsyncClient, ASGITransport

@pytest.fixture
def async_client():
    from app.main import app
    from app.services.knowledge_service import get_knowledge_service
    from app.services.knowledge_space_service import get_knowledge_space_service
    
    class DummyKnowledgeService:
        async def index_codebase(self):
            return {"message": "ok", "summary": "indexed"}
            
        async def get_stats(self):
            return {"nodes": 10, "edges": 5}
            
        async def get_code_entities(self, file_path=None):
            return [{"id": "1", "name": "ClassA", "type": "class", "file_path": "a.py"}]
            
        async def clear_graph(self):
            # To test error handling, if a special flag is set, raise an exception
            # Actually, we can just test the happy path, but let's test an exception.
            if hasattr(self, "should_fail") and self.should_fail:
                raise ValueError("Graph error")
            return 0
            
        async def semantic_query(self, query, limit=10):
            return "Mocked answer"
            
        async def reindex_graph(self, batch_size=50, labels=None):
            return 5
            
        async def get_node_types(self):
            return ["class", "function"]
            
        async def get_health_status(self):
            return {
                "status": "ok",
                "neo4j_connected": True,
                "qdrant_connected": True,
                "circuit_breaker_open": False,
                "total_nodes": 10,
                "total_relationships": 5
            }
            
        async def find_related_concepts(self, concept, max_depth=2, limit=10, skip=0):
            return [{"concept": "B", "relationship": "uses", "distance": 1}]
            
        async def get_entity_relationships(self, entity_name, rel_type=None, direction="both", max_depth=1, limit=20, skip=0):
            return [{"related_entity": "B", "related_type": "class", "relationship": "uses", "distance": 1}]
            
        async def ask_code_with_citations(self, question, limit=10, citation_limit=8):
            return {
                "answer": "Mocked",
                "citations": [
                    {"type": "class", "name": "A", "file_path": "a.py", "line": 1, "full_name": "A", "relevance": 1}
                ]
            }

    class DummyKnowledgeSpaceService:
        async def consolidate_experience(self, limit=10, min_score=0.0, **kwargs):
            return {"message": "ok", "stats": {"processed": 1}}

    app.dependency_overrides[get_knowledge_service] = lambda: DummyKnowledgeService()
    app.dependency_overrides[get_knowledge_space_service] = lambda: DummyKnowledgeSpaceService()
    
    # Mock memory DB and Circuit Breaker
    import app.core.memory.memory_core as mem_core
    original_get_memory_db = mem_core.get_memory_db
    
    class DummyMemoryDB:
        def reset_circuit_breaker(self):
            pass
        def get_circuit_breaker_status(self):
            return {"circuit_breaker_open": False, "offline": False}
            
    async def mock_get_memory_db(*args, **kwargs):
        return DummyMemoryDB()
        
    mem_core.get_memory_db = mock_get_memory_db
    
    client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    yield client
    
    mem_core.get_memory_db = original_get_memory_db
    app.dependency_overrides.clear()

@pytest.mark.asyncio
class TestKnowledgeEndpointsExtended:

    async def test_index_codebase(self, async_client):
        resp = await async_client.post("/api/v1/knowledge/index")
        assert resp.status_code == 200

    async def test_get_stats(self, async_client):
        resp = await async_client.get("/api/v1/knowledge/stats")
        assert resp.status_code == 200
        assert "nodes" in resp.json()

    async def test_get_entities(self, async_client):
        resp = await async_client.get("/api/v1/knowledge/entities")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    async def test_clear_graph(self, async_client):
        resp = await async_client.delete("/api/v1/knowledge/clear")
        assert resp.status_code == 200
        assert resp.json()["status"] == "success"

    async def test_clear_graph_error(self, async_client):
        import app.services.knowledge_service as ks
        from app.main import app
        
        class FailingKnowledgeService:
            async def clear_graph(self):
                raise ValueError("Graph error")
                
        app.dependency_overrides[ks.get_knowledge_service] = lambda: FailingKnowledgeService()
        
        resp = await async_client.delete("/api/v1/knowledge/clear")
        assert resp.status_code == 400
        assert "Graph error" in resp.json()["detail"]
            
        # We don't necessarily need to restore it because fixture clears it, but let's be safe
        app.dependency_overrides.pop(ks.get_knowledge_service, None)

    async def test_reset_circuit_breaker_error(self, async_client):
        import app.core.memory.memory_core as mem_core
        
        class FailingMemoryDB:
            def reset_circuit_breaker(self):
                raise RuntimeError("CB failure")
                
        orig = mem_core.get_memory_db
        async def failing_get_memory_db(*args, **kwargs):
            return FailingMemoryDB()
        mem_core.get_memory_db = failing_get_memory_db
        
        # It handles Exception and raises HTTPException(500)
        resp = await async_client.post("/api/v1/knowledge/health/reset-circuit-breaker")
        assert resp.status_code == 500
        assert "CB failure" in resp.json()["detail"]
        
        mem_core.get_memory_db = orig

    async def test_query_code_with_no_citations(self, async_client):
        import app.services.knowledge_service as ks
        from app.main import app
        
        class EmptyKnowledgeService:
            async def ask_code_with_citations(self, question, limit=10, citation_limit=8):
                return {"answer": "No citations", "citations": []}
                
        app.dependency_overrides[ks.get_knowledge_service] = lambda: EmptyKnowledgeService()
        
        resp = await async_client.post("/api/v1/knowledge/query/code", json={"question": "test"})
        assert resp.status_code == 200
        assert "Nao encontrei citacoes" in resp.json()["answer"]
        
        app.dependency_overrides.pop(ks.get_knowledge_service, None)

    async def test_query_knowledge(self, async_client):
        resp = await async_client.post("/api/v1/knowledge/query", json={"query": "test"})
        assert resp.status_code == 200
        assert resp.json()["answer"] == "Mocked answer"

    async def test_query_code_with_citations(self, async_client):
        resp = await async_client.post("/api/v1/knowledge/query/code", json={"question": "test"})
        assert resp.status_code == 200
        assert "citations" in resp.json()

    async def test_related_concepts(self, async_client):
        resp = await async_client.post("/api/v1/knowledge/concepts/related", json={"concept": "A"})
        assert resp.status_code == 200
        assert "results" in resp.json()

    async def test_reindex_concepts(self, async_client):
        resp = await async_client.post("/api/v1/knowledge/concepts/reindex", json={})
        assert resp.status_code == 200
        assert resp.json()["status"] == "success"

    async def test_get_node_types(self, async_client):
        resp = await async_client.get("/api/v1/knowledge/node-types")
        assert resp.status_code == 200
        assert "types" in resp.json()

    async def test_knowledge_health(self, async_client):
        resp = await async_client.get("/api/v1/knowledge/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    async def test_reset_circuit_breaker(self, async_client):
        resp = await async_client.post("/api/v1/knowledge/health/reset-circuit-breaker")
        assert resp.status_code == 200

    async def test_detailed_health(self, async_client):
        resp = await async_client.get("/api/v1/knowledge/health/detailed")
        assert resp.status_code == 200
        assert resp.json()["overall_status"] == "healthy"

    async def test_entity_relationships(self, async_client):
        resp = await async_client.get("/api/v1/knowledge/entity/ClassA/relationships")
        assert resp.status_code == 200
        assert "results" in resp.json()

    async def test_consolidate(self, async_client):
        resp = await async_client.post("/api/v1/knowledge/consolidate", json={"mode": "batch"})
        assert resp.status_code == 200
        assert resp.json()["message"] == "Tarefa de consolidação publicada."
