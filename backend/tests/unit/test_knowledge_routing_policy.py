from app.core.routing import RouteIntent, RouteTarget, load_knowledge_routing_policy


def test_hybrid_route_uses_qdrant_with_neo4j_fallback():
    policy = load_knowledge_routing_policy()

    decision = policy.resolve(
        RouteIntent.RAG_HYBRID_SEARCH,
        include_graph=True,
        query="what changed in architecture",
    )

    assert decision.primary == RouteTarget.QDRANT
    assert RouteTarget.NEO4J in decision.secondary
    assert decision.rule_id == "rag.hybrid.qdrant_plus_neo4j"


def test_hybrid_route_keeps_global_code_path():
    policy = load_knowledge_routing_policy()

    decision = policy.resolve(
        RouteIntent.RAG_HYBRID_SEARCH,
        include_graph=True,
        query="memory_core",
    )

    assert decision.primary == RouteTarget.QDRANT
    assert RouteTarget.NEO4J in decision.secondary
    assert not decision.rule_id.endswith(".missing_user_fallback")


def test_unknown_intent_uses_default_postgres_route():
    policy = load_knowledge_routing_policy()

    decision = policy.resolve("unknown_intent")

    assert decision.primary == RouteTarget.POSTGRES
    assert decision.rule_id == "default.postgres_only"
