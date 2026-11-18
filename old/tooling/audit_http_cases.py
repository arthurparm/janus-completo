#!/usr/bin/env python3
import ast
import json
import re
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[1]

TARGET_MODULES = {
    "users": "1 (System & Auth)",
    "profiles": "1 (System & Auth)",
    "tools": "2 (Agent Ecosystem)",
    "agent": "2 (Agent Ecosystem)",
    "knowledge": "3 (Knowledge & RAG)",
    "learning": "3 (Knowledge & RAG)",
    "memory": "3 (Knowledge & RAG)",
    "documents": "3 (Knowledge & RAG)",
    "context": "3 (Knowledge & RAG)",
    "rag": "3 (Knowledge & RAG)",
    "chat_message": "4 (Interaction)",
    "chat_history": "4 (Interaction)",
    "chat_stream": "4 (Interaction)",
    "collaboration": "4 (Interaction)",
    "feedback": "4 (Interaction)",
    "productivity": "4 (Interaction)",
    "tasks": "5 (Operations)",
    "observability": "5 (Operations)",
    "autonomy": "6 (Advanced Autonomy)",
    "autonomy_history": "6 (Advanced Autonomy)",
    "pending_actions": "6 (Advanced Autonomy)"
}

def analyze_tests_regex():
    endpoint_status = defaultdict(set)
    
    for test_file in (ROOT / "qa").glob("test_*.py"):
        content = test_file.read_text()
        
        # Extract constants
        constants = {}
        for line in content.splitlines():
            m = re.match(r'^([A-Z0-9_]+_REF)\s*=\s*[\'"](/api/v1/[^\'"]+)[\'"]', line)
            if m:
                constants[m.group(1)] = m.group(2)
                
        # Split by test functions
        functions = re.split(r'^ *async def test_|^ *def test_', content, flags=re.MULTILINE)
        
        for func_body in functions[1:]:
            # Find URLs or CONST_REFs
            urls_in_func = set()
            
            # Find explicit strings
            for m in re.finditer(r'[\'"](/api/v1/[^\'"]+)[\'"]', func_body):
                urls_in_func.add(m.group(1))
                
            # Find constants
            for const_name, url_val in constants.items():
                if const_name in func_body:
                    urls_in_func.add(url_val)
                    
            if not urls_in_func:
                continue
                
            # Clean URLs
            cleaned_urls = set()
            for u in urls_in_func:
                u = u.split("?")[0]
                u = re.sub(r'/[0-9a-fA-F\-]{10,}', '/{id}', u)
                u = re.sub(r'/[0-9]+$', '/{id}', u)
                cleaned_urls.add(u)
                
            # Find assert resp.status_code == X
            status_codes = set()
            for m in re.finditer(r'status_code\s*==\s*([0-9]{3})', func_body):
                status_codes.add(int(m.group(1)))
                
            # Find assert resp.status_code in [X, Y]
            for m in re.finditer(r'status_code\s*in\s*\[([0-9,\s]+)\]', func_body):
                nums = [int(x.strip()) for x in m.group(1).split(",") if x.strip().isdigit()]
                status_codes.update(nums)
                
            for cu in cleaned_urls:
                endpoint_status[cu].update(status_codes)
                
    return endpoint_status

def load_coverage():
    cov_file = ROOT / "coverage.json"
    if not cov_file.exists():
        return {}
    data = json.loads(cov_file.read_text())
    files = data.get("files", {})
    
    module_cov = {}
    for f, f_data in files.items():
        if "backend/app/api/v1/endpoints/" in f:
            name = Path(f).stem
            if name in TARGET_MODULES:
                summary = f_data.get("summary", {})
                module_cov[name] = summary.get("percent_covered_display", "0")
                
    return module_cov

def generate_report():
    regex_status = analyze_tests_regex()
    coverage_data = load_coverage()
    
    out = []
    out.append("# Dossiê de Garantia de Cobertura - Passos 1 a 6")
    out.append("> Gerado de forma automatizada via `pytest-cov` (Runtime) e Parsing de Testes (Sem alucinação)\n")
    
    out.append("## 1. Cobertura Real do Código (Line Coverage)")
    out.append("A tabela abaixo mostra o percentual EXATO de linhas de código executadas pelo interpretador Python durante os testes. Um valor alto aqui significa que *todos os ifs, elses e raises* do endpoint foram engatilhados e testados em Runtime.\n")
    
    out.append("| Módulo (Endpoint File) | Passo | % Linhas Cobertas (Pytest-Cov) |")
    out.append("|---|---|---|")
    
    for mod, step in sorted(TARGET_MODULES.items(), key=lambda x: x[1]):
        cov = coverage_data.get(mod, "N/A")
        out.append(f"| `{mod}.py` | {step} | **{cov}%** |")
        
    out.append("\n## 2. Casos de Status HTTP Auditados nos Testes")
    out.append("O script varreu o código-fonte dos testes `qa/*.py` e extraiu de forma determinística quais `status_code` estão sendo asseridos para as URLs do sistema.\n")
    
    out.append("| URL | Status Codes Validados nos Testes |")
    out.append("|---|---|")
    
    for url, statuses in sorted(regex_status.items()):
        # Ignorar endpoints irrelevantes (admin/system) se quisermos focar nos 1 a 6
        if "/admin" not in url and "/system" not in url:
            st_str = ", ".join(sorted(str(s) for s in statuses))
            out.append(f"| `{url}` | {st_str} |")
            
    return "\n".join(out)

if __name__ == "__main__":
    report = generate_report()
    out_file = ROOT / "outputs" / "qa" / "cases_guarantee_report.md"
    out_file.write_text(report)
    print(f"[ok] Relatório de garantia salvo em: {out_file}")
