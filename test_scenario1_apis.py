import requests
import json
import sys

BASE_URL = "http://localhost:8000/api/v1"

# APIs to test for Scenario 1
endpoints = [
    ("GET", "/system/status"),
    ("GET", "/system/health/services"),
    ("GET", "/system/overview"),
    ("GET", "/system/db/validate"),
    ("GET", "/knowledge/health"),
    ("GET", "/knowledge/health/detailed"),
]

results = []

print("🔍 Testing Scenario 1 APIs...\n")
print("=" * 70)

for method, path in endpoints:
    url = f"{BASE_URL}{path}"
    try:
        if method == "GET":
            response = requests.get(url, timeout=10)
        else:
            response = requests.post(url, timeout=10)

        status = "✅" if response.status_code == 200 else "⚠️"

        result = {
            "endpoint": path,
            "method": method,
            "status_code": response.status_code,
            "success": response.status_code == 200,
            "response_size": len(response.text),
        }

        # Try to parse JSON
        try:
            data = response.json()
            result["has_data"] = bool(data)
            result["sample"] = str(data)[:200] + "..." if len(str(data)) > 200 else str(data)
        except:
            result["has_data"] = False
            result["sample"] = response.text[:200]

        results.append(result)

        print(f"{status} {method:6} {path}")
        print(f"   Status: {response.status_code}")
        print(f"   Size: {len(response.text)} bytes")
        if result.get("sample"):
            print(f"   Sample: {result['sample']}")
        print()

    except Exception as e:
        results.append({
            "endpoint": path,
            "method": method,
            "success": False,
            "error": str(e)
        })
        print(f"❌ {method:6} {path}")
        print(f"   Error: {e}")
        print()

print("=" * 70)
print(f"\n📊 Summary: {sum(1 for r in results if r.get('success'))} / {len(results)} passed\n")

# Save detailed results
with open("api_test_results.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print("💾 Detailed results saved to: api_test_results.json")

# Exit with error if any failed
if not all(r.get("success") for r in results):
    sys.exit(1)
