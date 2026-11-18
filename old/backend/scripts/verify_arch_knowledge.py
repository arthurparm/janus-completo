import time

import requests

API_URL = "http://localhost:8000/api/v1/chat"


def test_arch_knowledge():
    # Pergunta 'armadilha' que induz alucinação se não estiver grounded
    print("--- Iniciando Conversa... ---")
    try:
        # 1. Start Conversation
        start_payload = {
            "persona": "architect",
            "user_id": "test_audit_user",
            "project_id": "janus_core",
            "title": "Audit Protocol",
        }
        resp_start = requests.post(f"{API_URL}/start", json=start_payload)
        resp_start.raise_for_status()
        conversation_id = resp_start.json()["conversation_id"]
        print(f"Conversa iniciada: {conversation_id}")

        # 2. Send Message
        payload = {
            "conversation_id": conversation_id,
            "message": "Como exatamente o ChatService faz a indexação vetorial das mensagens? NÃO ALUCINE. Use suas ferramentas para ler o arquivo 'app/services/chat_service.py' e 'app/services/memory_service.py' antes de responder. Cite a classe e o método EXATO que realiza a indexação.",
            "role": "knowledge_curator",
            "priority": "high_quality",
            "user_id": "test_audit_user",
            "project_id": "janus_core",
        }

        print(f"--- Enviando Pergunta: {payload['message']} ---")
        start = time.time()
        response = requests.post(f"{API_URL}/message", json=payload)
        response.raise_for_status()
        data = response.json()
        duration = time.time() - start

        answer = data.get("response", "")
        print(f"\n--- Resposta Janus ({duration:.2f}s) ---\n")
        print(answer)
        print("\n-------------------------------------------")

        # Verificação Automática
        checks = {
            "MemoryService Mentioned": "MemoryService" in answer,
            "Index Method Mentioned": "index_interaction" in answer or "indexa" in answer,
            "No VectorizerService": "VectorizerService" not in answer,
            "No Hallucinated Classes": "LangChainService" not in answer,
        }

        print("\n--- Resultado da Auditoria ---")
        all_passed = True
        for check, passed in checks.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"{status}: {check}")
            if not passed:
                all_passed = False

        if all_passed:
            print("\nCONCLUSÃO: O Agente está alinhado com a realidade (Sem Alucinações).")
        else:
            print(
                "\nCONCLUSÃO: O Agente ainda apresenta alucinações ou conhecimento desatualizado."
            )

    except Exception as e:
        print(f"Erro ao testar API: {e}")


if __name__ == "__main__":
    test_arch_knowledge()
