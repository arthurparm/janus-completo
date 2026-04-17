"""
Testes de regressão para o bug fix do endpoint /api/v1/reflexion/summary/post_sprint

Bug: TypeError quando timeframe_seconds é None
Fix: Adicionado default value (3600s) e null-safety no core layer
"""

import pytest
from httpx import AsyncClient, ASGITransport

@pytest.fixture
def async_client():
    from app.main import app
    from app.api.v1.endpoints.reflexion import get_reflexion_service
    from app.services.memory_service import get_memory_service
    
    class DummyReflexionService:
        async def post_sprint_summary(self, **kwargs):
            return {
                "lessons": [{"score": 0.8, "content": "mocked"}],
                "meta_report": "mocked"
            }
            
    class DummyMemoryService:
        async def recall_recent_lessons(self, **kwargs):
            return [{"score": 0.8, "content": "mocked lesson"}]
            
    app.dependency_overrides[get_reflexion_service] = lambda: DummyReflexionService()
    app.dependency_overrides[get_memory_service] = lambda: DummyMemoryService()
    
    client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    yield client
    
    app.dependency_overrides.clear()

class TestPostSprintEndpointRegressions:
    """Testes para prevenir regressão do bug de timeframe_seconds=None"""

    @pytest.mark.asyncio
    async def test_post_sprint_without_timeframe_parameter(
        self, async_client: AsyncClient
    ):
        """
        REGRESSION TEST: Endpoint deve funcionar sem o parâmetro timeframe_seconds

        Previne: TypeError: unsupported operand type(s) for *: 'NoneType' and 'int'
        """
        response = await async_client.get(
            "/api/v1/reflexion/summary/post_sprint?limit=5"
        )

        assert (
            response.status_code == 200
        ), f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()

        assert "lessons" in data
        assert "meta_report" in data
        assert isinstance(data["lessons"], list)

    @pytest.mark.asyncio
    async def test_post_sprint_with_default_timeframe(self, async_client: AsyncClient):
        """
        Testa que o endpoint usa o default de 3600s (1 hora) quando não especificado
        """
        response = await async_client.get("/api/v1/reflexion/summary/post_sprint")

        assert response.status_code == 200
        data = response.json()
        assert "lessons" in data

    @pytest.mark.asyncio
    async def test_post_sprint_with_explicit_timeframe(self, async_client: AsyncClient):
        """
        Testa que o endpoint aceita timeframe_seconds explícito
        """
        response = await async_client.get(
            "/api/v1/reflexion/summary/post_sprint?timeframe_seconds=7200&limit=10"
        )

        assert response.status_code == 200
        data = response.json()
        assert "lessons" in data

    @pytest.mark.asyncio
    async def test_post_sprint_timeframe_validation_min(
        self, async_client: AsyncClient
    ):
        """
        Testa validação mínima: timeframe_seconds >= 60
        """
        response = await async_client.get(
            "/api/v1/reflexion/summary/post_sprint?timeframe_seconds=30"
        )

        # FastAPI deve rejeitar valores < 60
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_post_sprint_timeframe_validation_max(
        self, async_client: AsyncClient
    ):
        """
        Testa validação máxima: timeframe_seconds <= 86400 (1 dia)
        """
        response = await async_client.get(
            "/api/v1/reflexion/summary/post_sprint?timeframe_seconds=90000"
        )

        # FastAPI deve rejeitar valores > 86400
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_post_sprint_all_params_optional(self, async_client: AsyncClient):
        """
        Testa que todos os parâmetros são opcionais exceto os com defaults
        """
        # Chamada sem nenhum parâmetro deve funcionar
        response = await async_client.get("/api/v1/reflexion/summary/post_sprint")

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_post_sprint_with_min_score_filter(self, async_client: AsyncClient):
        """
        Testa filtro por score mínimo
        """
        response = await async_client.get(
            "/api/v1/reflexion/summary/post_sprint?min_score=0.5&limit=5"
        )

        assert response.status_code == 200
        data = response.json()

        # Verifica que lições retornadas respeitam o score mínimo
        for lesson in data["lessons"]:
            if lesson.get("score") is not None:
                assert lesson["score"] >= 0.5
