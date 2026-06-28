import os
import sys

# Ensure "app" package is discoverable when running from repo root
sys.path.append(os.path.join(os.getcwd(), "backend"))


def test_knowledge_router_import_contract():
    from app.api.v1.endpoints.knowledge import router

    paths = {route.path for route in router.routes if hasattr(route, "path")}

    assert "/query" in paths
    assert "/health" in paths
    assert "/experimental/health" in paths
    assert "/spaces" in paths
    assert "/spaces/{knowledge_space_id}/query" in paths
