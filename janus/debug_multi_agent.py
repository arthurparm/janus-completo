import sys
import os
import asyncio
from unittest.mock import AsyncMock, patch

# Adiciona o diretório atual ao path para imports funcionarem
sys.path.append(os.getcwd())

async def run_test():
    print("Iniciando teste manual...")
    try:
        from app.core.agents.multi_agent_system import MultiAgentSystem, AgentRole, Task
        print("Import de MultiAgentSystem com sucesso.")
        
        # Mock broker
        with patch("app.core.agents.multi_agent_system.get_broker", new_callable=AsyncMock) as mock_broker_getter:
            broker_instance = AsyncMock()
            mock_broker_getter.return_value = broker_instance
            
            mas = MultiAgentSystem()
            print("MultiAgentSystem instanciado.")
            
            # Mock actor start
            with patch("app.core.agents.agent_actor.AgentActor.start", new_callable=AsyncMock):
                coder = mas.create_agent(AgentRole.CODER)
                print(f"Agente criado: {coder.agent_id}")
            
            task = Task(description="Test Task", assigned_to=coder.agent_id)
            mas.workspace.add_task(task)
            
            await mas.dispatch_task(task)
            print("Tarefa despachada.")
            
            if broker_instance.publish.called:
                print("SUCESSO: publish chamado.")
            else:
                print("FALHA: publish não chamado.")
                
    except Exception as e:
        print(f"ERRO FATAL: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run_test())
