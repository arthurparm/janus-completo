from prometheus_client import Counter, Histogram, Gauge

# Métricas específicas do chat

CHAT_MESSAGES_TOTAL = Counter(
    "chat_messages_total",
    "Total de mensagens processadas no chat",
    ["role", "outcome"],
)

CHAT_CONVERSATIONS_ACTIVE = Gauge(
    "chat_conversations_active",
    "Conversas ativas (existentes no repositório)",
)

CHAT_LATENCY_SECONDS = Histogram(
    "chat_message_latency_seconds",
    "Latência para processar uma mensagem do chat",
    ["role", "outcome"],
)

CHAT_TOKENS_TOTAL = Counter(
    "chat_tokens_total",
    "Tokens aproximados por direção no chat",
    ["direction"],
)

CHAT_SPEND_USD_TOTAL = Counter(
    "chat_spend_usd_total",
    "Gasto aproximado em USD por mensagem do chat",
    ["kind"],  # kind: "user" | "project"
)


def update_active_conversations(count: int) -> None:
    try:
        CHAT_CONVERSATIONS_ACTIVE.set(float(count))
    except Exception:
        # evitar quebra por métricas
        pass
