import importlib.util
from pathlib import Path


MODULE_PATH = (
    Path(__file__).resolve().parents[1] / "tooling" / "generate_api_coverage_report.py"
)
MODULE_SPEC = importlib.util.spec_from_file_location("generate_api_coverage_report", MODULE_PATH)
assert MODULE_SPEC and MODULE_SPEC.loader
coverage = importlib.util.module_from_spec(MODULE_SPEC)
MODULE_SPEC.loader.exec_module(coverage)


def _matrix(endpoints):
    return {
        "metadata": {
            "generated_at": "2026-02-21T00:00:00+00:00",
            "source": "openapi_live",
        },
        "endpoints": endpoints,
    }


def test_build_coverage_report_counts_and_target_gap():
    matrix = _matrix(
        [
            {
                "method": "GET",
                "path": "/api/v1/a",
                "module": "ModuleA",
                "referenced_in_tests": True,
                "smoke_success": None,
            },
            {
                "method": "POST",
                "path": "/api/v1/b",
                "module": "ModuleA",
                "referenced_in_tests": False,
                "smoke_success": True,
            },
            {
                "method": "DELETE",
                "path": "/api/v1/c",
                "module": "ModuleB",
                "referenced_in_tests": False,
                "smoke_success": False,
                "smoke_status_code": 500,
            },
            {
                "method": "GET",
                "path": "/api/v1/d",
                "module": "ModuleB",
                "referenced_in_tests": False,
                "smoke_success": None,
            },
        ]
    )

    report = coverage.build_coverage_report(matrix, expected_endpoints=5)

    assert report["summary"]["total_endpoints"] == 4
    assert report["summary"]["covered_endpoints"] == 3
    assert report["summary"]["uncovered_endpoints"] == 1
    assert report["summary"]["coverage_percent"] == 75.0
    assert report["summary"]["runtime_validated_endpoints"] == 1
    assert report["summary"]["runtime_failed_endpoints"] == 1
    assert report["summary"]["test_referenced_endpoints"] == 1

    assert report["target"]["expected_endpoints"] == 5
    assert report["target"]["observed_endpoints"] == 4
    assert report["target"]["target_met"] is False
    assert report["target"]["endpoint_gap"] == 1

    assert len(report["runtime_failed_endpoints"]) == 1
    assert report["runtime_failed_endpoints"][0]["path"] == "/api/v1/c"
    assert len(report["uncovered_endpoints"]) == 1
    assert report["uncovered_endpoints"][0]["path"] == "/api/v1/d"


def test_render_markdown_includes_summary_sections():
    matrix = _matrix(
        [
            {
                "method": "GET",
                "path": "/api/v1/a",
                "module": "ModuleA",
                "referenced_in_tests": True,
                "smoke_success": None,
            }
        ]
    )
    report = coverage.build_coverage_report(matrix, expected_endpoints=1)
    markdown = coverage.render_markdown(report)

    assert "# API Coverage Report (OQ-011)" in markdown
    assert "## Summary" in markdown
    assert "## Coverage By Module" in markdown
    assert "## Target Tracking" in markdown
    assert "`100.0%`" in markdown


def test_parse_docker_ps_output_accepts_ndjson():
    raw = '{"Name":"janus_api","State":"running"}\n{"Name":"janus_postgres","State":"running"}\n'
    rows = coverage.parse_docker_ps_output(raw)
    assert len(rows) == 2
    assert rows[0]["Name"] == "janus_api"
