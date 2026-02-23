#!/usr/bin/env python3
"""
API Inventory Extraction Script
Fetches OpenAPI spec from running Janus backend and generates structured inventory.
"""

import json
import requests
from typing import Dict, List, Any
from datetime import datetime
from pathlib import Path


def fetch_openapi_spec(base_url: str = "http://localhost:8000") -> Dict[str, Any]:
    """Fetch OpenAPI specification from running backend."""
    try:
        response = requests.get(f"{base_url}/openapi.json", timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ Erro ao buscar OpenAPI spec: {e}")
        print("⚠️ Certifique-se que o backend está rodando: docker-compose up -d")
        raise


def extract_endpoints(openapi_spec: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract structured endpoint information from OpenAPI spec."""
    endpoints = []
    paths = openapi_spec.get("paths", {})

    for path, methods in paths.items():
        # Skip non-API paths
        if not path.startswith("/api/v1/"):
            continue

        for method, details in methods.items():
            if method.lower() not in ["get", "post", "put", "patch", "delete"]:
                continue

            # Extract metadata
            endpoint = {
                "path": path,
                "method": method.upper(),
                "operation_id": details.get("operationId", ""),
                "summary": details.get("summary", ""),
                "tags": details.get("tags", []),
                "module": details.get("tags", ["unknown"])[0] if details.get("tags") else "unknown",

                # Request info
                "requires_auth": bool(
                    details.get("security") or "Bearer" in str(details)
                ),
                "request_body_schema": None,
                "parameters": [],

                # Response info
                "response_schemas": {},

                # Coverage tracking (to be filled by other scripts)
                "has_frontend": None,  # Unknown initially
                "has_tests": None,     # Unknown initially
                "tier": None,          # funcional/básico/perfeito
                "priority": None,      # P0/P1/P2/P3
                "user_impact": None,   # high/medium/low
            }

            # Extract request body schema
            if "requestBody" in details:
                content = details["requestBody"].get("content", {})
                if "application/json" in content:
                    schema_ref = content["application/json"].get("schema", {})
                    endpoint["request_body_schema"] = schema_ref.get("$ref", str(schema_ref))

            # Extract parameters
            if "parameters" in details:
                endpoint["parameters"] = [
                    {
                        "name": param.get("name"),
                        "in": param.get("in"),  # query, path, header
                        "required": param.get("required", False),
                        "schema": param.get("schema", {}).get("type", "unknown")
                    }
                    for param in details["parameters"]
                ]

            # Extract response schemas
            if "responses" in details:
                for status_code, response in details["responses"].items():
                    content = response.get("content", {})
                    if "application/json" in content:
                        schema = content["application/json"].get("schema", {})
                        endpoint["response_schemas"][status_code] = schema.get("$ref", str(schema))

            endpoints.append(endpoint)

    return endpoints


def generate_statistics(endpoints: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate summary statistics from endpoints."""
    stats = {
        "total_endpoints": len(endpoints),
        "by_method": {},
        "by_module": {},
        "by_auth": {
            "requires_auth": 0,
            "public": 0
        },
        "extraction_timestamp": datetime.now().isoformat(),
    }

    for endpoint in endpoints:
        # Method stats
        method = endpoint["method"]
        stats["by_method"][method] = stats["by_method"].get(method, 0) + 1

        # Module stats
        module = endpoint["module"]
        stats["by_module"][module] = stats["by_module"].get(module, 0) + 1

        # Auth stats
        if endpoint["requires_auth"]:
            stats["by_auth"]["requires_auth"] += 1
        else:
            stats["by_auth"]["public"] += 1

    return stats


def save_inventory(endpoints: List[Dict[str, Any]], output_path: Path):
    """Save inventory to JSON file."""
    stats = generate_statistics(endpoints)

    inventory = {
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "source": "OpenAPI Specification",
            "version": "1.0"
        },
        "statistics": stats,
        "endpoints": endpoints
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(inventory, f, indent=2, ensure_ascii=False)

    print(f"✅ Inventário salvo em: {output_path}")
    return stats


def print_summary(stats: Dict[str, Any]):
    """Print human-readable summary."""
    print("\n" + "="*60)
    print("📊 RESUMO DO INVENTÁRIO DE APIs")
    print("="*60)
    print(f"\n🎯 Total de Endpoints: {stats['total_endpoints']}")

    print("\n📋 Por Método HTTP:")
    for method, count in sorted(stats['by_method'].items()):
        print(f"  {method:6} → {count:3} endpoints")

    print("\n🏗️ Por Módulo:")
    for module, count in sorted(stats['by_module'].items(), key=lambda x: -x[1]):
        print(f"  {module:20} → {count:3} endpoints")

    print("\n🔐 Autenticação:")
    print(f"  Requer Auth → {stats['by_auth']['requires_auth']} endpoints")
    print(f"  Público     → {stats['by_auth']['public']} endpoints")

    print("\n⏰ Gerado em: {0}".format(stats['extraction_timestamp']))
    print("="*60 + "\n")


def main():
    """Main execution flow."""
    print("🚀 Iniciando extração do inventário de APIs...\n")

    # Configuration
    base_url = "http://localhost:8000"
    output_file = Path(__file__).parent.parent / "outputs" / "qa" / "api_inventory.json"

    # Fetch and process
    print(f"📡 Buscando OpenAPI spec de {base_url}...")
    openapi_spec = fetch_openapi_spec(base_url)

    print(f"🔍 Extraindo endpoints de /api/v1/...")
    endpoints = extract_endpoints(openapi_spec)

    print(f"💾 Salvando inventário...")
    stats = save_inventory(endpoints, output_file)

    # Print summary
    print_summary(stats)

    print(f"✨ Inventário completo disponível em: {output_file}\n")


if __name__ == "__main__":
    main()
