import os
import re
import ast
import sys

# Configuration
SEARCH_DIR = "backend/app"
EXCLUDE_DIRS = ["tests", "venv", "__pycache__", "migrations", "alembic"]
PII_KEYWORDS = ["password", "token", "secret", "cpf", "email", "credit_card", "senha"]
SECRET_PATTERNS = [
    r"API_KEY\s*=\s*['\"][A-Za-z0-9_\-]{20,}['\"]",
    r"PASSWORD\s*=\s*['\"][^'\"]{8,}['\"]",
    r"SECRET\s*=\s*['\"][^'\"]{8,}['\"]",
]

def is_excluded(path):
    parts = path.split(os.sep)
    for exclude in EXCLUDE_DIRS:
        if exclude in parts:
            return True
    return False

def scan_pii_logging(content):
    findings = []
    lines = content.splitlines()
    for i, line in enumerate(lines):
        if "logger" in line or "print" in line:
            for keyword in PII_KEYWORDS:
                if keyword in line.lower():
                    # heuristic to avoid false positives in variable names if not logging value
                    findings.append(f"Line {i+1}: Potential PII logging ('{keyword}')")
    return findings

def scan_hardcoded_secrets(content):
    findings = []
    for pattern in SECRET_PATTERNS:
        matches = re.finditer(pattern, content)
        for match in matches:
            findings.append(f"Potential hardcoded secret found: {match.group(0)[:20]}...")
    return findings

def scan_api_endpoints(filepath, content):
    findings = []
    if "backend/app/api/v1/endpoints" not in filepath:
        return findings

    try:
        tree = ast.parse(content)
    except SyntaxError:
        return [f"Could not parse file for AST analysis."]

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            is_route = False
            has_limiter = False

            # Check decorators
            for decorator in node.decorator_list:
                # Handle @router.get(...)
                if isinstance(decorator, ast.Call):
                    func = decorator.func
                    if isinstance(func, ast.Attribute):
                        if func.attr in ['get', 'post', 'put', 'delete', 'patch']:
                            is_route = True
                    elif isinstance(func, ast.Name):
                        if func.id in ['get', 'post', 'put', 'delete', 'patch']:
                            is_route = True

                    # Check for limiter
                    if isinstance(func, ast.Attribute) and func.attr == 'limit':
                        has_limiter = True
                    if isinstance(func, ast.Name) and func.id == 'limit':
                        has_limiter = True

            if is_route:
                # Check arguments for Depends(get_current_user)
                has_auth = False

                # Check if "get_current_user" is mentioned in arguments or defaults
                # This is a heuristic because fully parsing TypeHints/Defaults is complex
                func_source = ast.get_source_segment(content, node)
                if func_source:
                    if "get_current_user" in func_source:
                        has_auth = True
                    if "limiter.limit" in func_source:
                        has_limiter = True

                # Allow public endpoints explicitly
                if any(x in node.name for x in ["login", "register", "health", "reset", "public"]):
                    has_auth = True

                if not has_auth:
                    findings.append(f"Endpoint '{node.name}' might be missing AuthZ (get_current_user).")

                if not has_limiter:
                     findings.append(f"Endpoint '{node.name}' might be missing Rate Limiting (@limiter.limit).")

    return findings

def main():
    report = {}

    print(f"Starting security scan on {SEARCH_DIR}...")

    for root, dirs, files in os.walk(SEARCH_DIR):
        if is_excluded(root):
            continue

        for file in files:
            if not file.endswith(".py"):
                continue

            filepath = os.path.join(root, file)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()

                file_findings = []
                file_findings.extend(scan_pii_logging(content))
                file_findings.extend(scan_hardcoded_secrets(content))
                file_findings.extend(scan_api_endpoints(filepath, content))

                if file_findings:
                    report[filepath] = file_findings
            except Exception as e:
                print(f"Error scanning {filepath}: {e}", file=sys.stderr)

    # Output Report
    if report:
        print("\n=== SECURITY SCAN REPORT ===\n")
        for filepath, issues in report.items():
            print(f"File: {filepath}")
            for issue in issues:
                print(f"  - {issue}")
        print(f"\nFound issues in {len(report)} files.")
    else:
        print("\nNo obvious security issues found (clean run).")

if __name__ == "__main__":
    main()
