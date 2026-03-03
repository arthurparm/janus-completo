from app.core.routing import RouteIntent, RouteTarget, load_knowledge_routing_policy


def test_hybrid_route_uses_qdrant_with_neo4j_fallback():
    policy = load_knowledge_routing_policy()

    decision = policy.resolve(
        RouteIntent.RAG_HYBRID_SEARCH,
        user_id="user-1",
        include_graph=True,
        query="what changed in architecture?",
    )

    assert decision.primary == RouteTarget.QDRANT
    assert RouteTarget.NEO4J in decision.secondary
    assert decision.rule_id == "rag.hybrid.qdrant_plus_neo4j"


def test_missing_user_id_falls_back_from_qdrant_to_postgres():
    policy = load_knowledge_routing_policy()

    decision = policy.resolve(
        RouteIntent.CHAT_CONTEXT_RETRIEVAL,
        user_id=None,
        include_graph=False,
        query="deploy in production",
    )

    assert decision.primary == RouteTarget.POSTGRES
    assert decision.rule_id.endswith(".missing_user_fallback")


def test_unknown_intent_uses_default_postgres_route():
    policy = load_knowledge_routing_policy()

    decision = policy.resolve("unknown_intent", user_id="u-1")

    assert decision.primary == RouteTarget.POSTGRES
    assert decision.rule_id == "default.postgres_only"
