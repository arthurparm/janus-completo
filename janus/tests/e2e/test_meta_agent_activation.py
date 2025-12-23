
import pytest
import httpx
import json
import logging
from app.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Base URL for Janus API running in Docker (localhost mapped port)
BASE_URL = "http://localhost:8000/api/v1"

@pytest.mark.asyncio
async def test_meta_agent_activation():
    """
    Testa a ativação do Meta-Agente via API REST.
    Este teste assume que o Janus backend está rodando em Docker e acessível em localhost:8000.
    """
    logger.info("Tentando ativar Meta-Agente/Self-Improvement via API Docker...")
    
    url = f"{BASE_URL}/meta-agent/analyze"
    logger.info(f"POST {url}")
    
    timeout = httpx.Timeout(120.0, connect=5.0)  # Analysis might take time
    
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url)
            
            if response.status_code == 404:
                pytest.fail(f"Endpoint não encontrado: {url}. Verifique se 'meta_agent' está habilitado e roteado.")
                
            if response.status_code != 200 and response.status_code != 202:
                # Se falhar, tenta imprimir o erro
                try:
                     error_detail = response.json()
                except:
                     error_detail = response.text
                pytest.fail(f"Falha ao ativar Meta-Agente. Status: {response.status_code}. Detalhes: {error_detail}")

            # Sucesso
            data = response.json()
            report = data.get("report")
            
            if not report:
                pytest.fail(f"Resposta sem relatório: {data}")

            logger.info("✓ Ciclo de análise do Meta-Agente concluído com sucesso!")
            
            # Print report summary nicely
            print("\n" + "="*60)
            print(f"RELATÓRIO DE AUTO-APERFEIÇOAMENTO (Ciclo: {report.get('cycle_id')})")
            print("="*60)
            print(f"Status Geral: {report.get('overall_status', 'UNKNOWN')}")
            print(f"Score de Saúde: {report.get('health_score', 0)}/100")
            
            issues = report.get('issues_detected', [])
            recommendations = report.get('recommendations', [])
            
            print(f"\nProblemas Detectados ({len(issues)}):")
            for issue in issues:
                print(f" - [{issue.get('severity', 'LOW').upper()}] {issue.get('title')}: {issue.get('description')}")
                
            print(f"\nRecomendações ({len(recommendations)}):")
            for rec in recommendations:
                print(f" - [P{rec.get('priority', 3)}] {rec.get('title')}: {rec.get('description')}")
                
            print("\nResumo Executivo:")
            print(report.get('summary'))
            print("="*60 + "\n")
            
            # Validate minimal report structure
            assert "overall_status" in report
            assert isinstance(issues, list)
            
    except httpx.ConnectError:
        pytest.fail(
            "Não foi possível conectar ao Janus em localhost:8000. "
            "Certifique-se de que o container Docker está rodando e a porta 8000 está mapeada."
        )
    except Exception as e:
        pytest.fail(f"Erro inesperado durante o teste: {e}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_meta_agent_activation())
