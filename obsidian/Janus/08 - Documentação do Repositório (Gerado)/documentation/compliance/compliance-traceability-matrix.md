---
gerado: true
origem: "documentation/compliance/compliance-traceability-matrix.md"
ultima_geracao: "2026-05-22T18:03:31.345032+00:00"
---

# Matriz de Rastreabilidade de Compliance (Internal-Only)

Classificação: internal-only  
Fonte canônica: [compliance-traceability-matrix.json](file:///h:/repos/janus-completo/documentation/compliance/compliance-traceability-matrix.json)

## Objetivo

Relacionar cada controle de compliance a evidências verificáveis no código e/ou nos testes automatizados, reduzindo “compliance washing” e acelerando auditorias.

## Como verificar

- Validação automática: `python tooling/validate_compliance_matrix.py`
- Evidência: cada item aponta para um arquivo existente no repositório (código/teste/doc operacional).
- Anti-compliance-washing: evidências podem incluir um `pattern` (regex) que deve existir no arquivo apontado.
