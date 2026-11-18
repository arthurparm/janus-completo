from prometheus_client import Counter, Gauge, Histogram

# --- Métricas ---
AGENT_TASKS_COUNTER = Counter(
    "multi_agent_tasks_total", "Total de tarefas executadas por agentes", ["agent_role", "status"]
)

AGENT_COLLABORATION_COUNTER = Counter(
    "multi_agent_collaborations_total",
    "Total de colaborações entre agentes",
    ["initiator", "collaborator"],
)

AGENT_TASK_DURATION = Histogram(
    "multi_agent_task_duration_seconds", "Duração de execução de tarefas por agente", ["agent_role"]
)

ACTIVE_AGENTS_GAUGE = Gauge("multi_agent_active_agents", "Número de agentes ativos no sistema")
