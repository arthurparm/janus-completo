# app/core/meta_agent_cycle.py
import asyncio
import logging

from app.core.agent_manager import agent_manager, AgentType

logger = logging.getLogger(__name__)

# O intervalo, em segundos, com que o Meta-Agente irá verificar o sistema.
# Para produção, este valor seria mais alto (ex: 3600 para 1 hora).
CYCLE_INTERVAL_SECONDS = 300  # 5 minutos para fins de teste


async def run_meta_agent_cycle():
    """
    Executa o ciclo de vida proativo do Meta-Agente em um loop infinito.
    """
    logger.info("Ciclo de vida do Meta-Agente iniciado. Primeira verificação em breve.")
    while True:
        try:
            await asyncio.sleep(CYCLE_INTERVAL_SECONDS)
            logger.info("=" * 80)
            logger.info("META-AGENTE: Iniciando ciclo de auto-análise...")

            # A tarefa inicial para o Meta-Agente
            initial_prompt = "Analise o estado atual do sistema em busca de padrões de falha."

            # Executa o Meta-Agente
            result = agent_manager.run_agent(
                question=initial_prompt,
                request=None,
                agent_type=AgentType.META_AGENT
            )

            final_answer = result.get("answer", "Nenhuma conclusão gerada.")

            logger.info(f"META-AGENTE: Análise concluída. Relatório: {final_answer}")
            logger.info("=" * 80)

            # Aqui, no futuro, poderíamos adicionar lógica para pegar a "recomendação de tarefa"
            # do Meta-Agente e criar uma nova tarefa para o TOOL_USER.

        except Exception as e:
            logger.error(f"Ocorreu um erro crítico no ciclo do Meta-Agente: {e}", exc_info=True)
            # Espera um intervalo mais longo antes de tentar novamente para evitar loops de erro rápidos.
            await asyncio.sleep(CYCLE_INTERVAL_SECONDS * 2)
