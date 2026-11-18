
import logging
import os

import httpx
import pytest

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# /api/v1/meta-agent/* is control-plane scoped and lives on the dedicated
# control-plane service, not the user-facing API on port 8000.
CONTROL_PLANE_URL = os.getenv("CONTROL_PLANE_BASE_URL", "http://localhost:8002/api/v1")


@pytest.mark.asyncio
async def test_meta_agent_analyze_requires_delegated_admin_authorization():
    """
    /api/v1/meta-agent/analyze e control-plane com escopo autonomy:admin.
    Mesmo um client_credentials valido do janus-admin-facade e rejeitado sem
    um contexto de delegacao humana ativo (X-Janus-Delegated-Subject /
    X-Janus-Delegation-ID resolvendo para um registro em has_active_admin_delegation).
    Nao existe hoje um fluxo automatizado para provisionar essa delegacao, entao
    este teste valida o invariante de seguranca (rejeitado sem delegacao) em vez
    de fingir um ciclo de ativacao bem-sucedido.
    """
    url = f"{CONTROL_PLANE_URL}/meta-agent/analyze"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url)
    except httpx.ConnectError:
        pytest.fail(
            f"Nao foi possivel conectar ao servico control-plane em {CONTROL_PLANE_URL}. "
            "Certifique-se de que janus_control_plane_pc1 esta rodando."
        )

    assert response.status_code == 401, (
        f"Esperado 401 (autenticacao obrigatoria) sem delegacao de admin, "
        f"recebido {response.status_code}: {response.text}"
    )
