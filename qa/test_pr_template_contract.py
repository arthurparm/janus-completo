from pathlib import Path


def test_pull_request_template_has_risk_and_evidence_sections():
    template = Path(".github/pull_request_template.md")
    assert template.exists(), "Expected PR template at .github/pull_request_template.md"

    content = template.read_text(encoding="utf-8")

    expected_markers = [
        "# Risco",
        "## Classificacao de risco",
        "## Riscos identificados e mitigacoes",
        "# Evidencias",
        "## Testes executados",
        "## Resultado dos testes",
        "## Validacao manual",
        "# Checklist final",
    ]
    for marker in expected_markers:
        assert marker in content, f"Missing required section in PR template: {marker}"

