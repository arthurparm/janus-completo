import os
import re
import ast

class SecurityScanner:
    def __init__(self, root_dirs, exclude_dirs, exclude_files):
        self.root_dirs = root_dirs
        self.exclude_dirs = exclude_dirs
        self.exclude_files = exclude_files
        self.findings = []

    def scan(self):
        for root_dir in self.root_dirs:
            if not os.path.exists(root_dir):
                print(f"Directory not found: {root_dir}")
                continue
            for root, dirs, files in os.walk(root_dir):
                # Modify dirs in-place to skip excluded directories
                dirs[:] = [d for d in dirs if d not in self.exclude_dirs and not d.startswith('.')]

                for file in files:
                    if file in self.exclude_files:
                        continue
                    if file.endswith(('.py', '.ts', '.js')):
                        self.scan_file(os.path.join(root, file))

    def scan_file(self, filepath):
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            self.check_pii_logging(filepath, content)
            self.check_hardcoded_secrets(filepath, content)

            if filepath.endswith('.py'):
                self.check_authz_backend(filepath, content)
                self.check_rate_limit(filepath, content)
                self.check_vulnerabilities_python(filepath, content)
                self.check_vulnerable_imports(filepath, content)

        except Exception as e:
            print(f"Error scanning {filepath}: {e}")

    def check_pii_logging(self, filepath, content):
        # Regex for logger.info/debug/etc or print with sensitive keywords
        # Looking for things like logger.info(f"User token: {token}")
        pattern = re.compile(r'(logger\.(info|debug|warning|error)|print)\s*\([^\)]*?\b(token|password|key|secret|email|cpf|phone)\b.*?\)', re.IGNORECASE | re.DOTALL)
        matches = pattern.finditer(content)
        for match in matches:
            line_num = content[:match.start()].count('\n') + 1
            self.findings.append({
                'type': 'PII/Token Logging',
                'file': filepath,
                'line': line_num,
                'detail': match.group(0)[:100].replace('\n', ' ')
            })

    def check_hardcoded_secrets(self, filepath, content):
        # Regex for assignments like PASSWORD = "..."
        # Avoid things like os.getenv("PASSWORD", "default") - looking for string literals
        # This is tricky, so we'll look for simple assignments
        pattern = re.compile(r'\b(PASSWORD|SECRET|KEY|TOKEN|API_KEY)\s*=\s*[\'"]([^\'"\s]+)[\'"]', re.IGNORECASE)
        matches = pattern.finditer(content)
        for match in matches:
            val = match.group(2)
            # Skip placeholders or env var calls if regex caught them (though specifically looking for string literals)
            if '{' in val or 'os.get' in val or 'config' in val:
                continue

            line_num = content[:match.start()].count('\n') + 1
            # Exclude test files or config examples if not already excluded
            if "test" in filepath or "example" in filepath:
                continue
            self.findings.append({
                'type': 'Hardcoded Secret',
                'file': filepath,
                'line': line_num,
                'detail': match.group(0)[:50]
            })

    def check_authz_backend(self, filepath, content):
        # Basic AST check for FastAPI routes without Depends
        if 'janus/app/api' not in filepath:
            return

        try:
            tree = ast.parse(content)
        except SyntaxError:
            return

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Check if it's a route
                is_route = False
                http_method = ""
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute):
                        if decorator.func.attr in ['get', 'post', 'put', 'delete', 'patch']:
                            is_route = True
                            http_method = decorator.func.attr
                            break

                if is_route:
                    has_auth = False

                    # Check decorator arguments (dependencies=[Depends(...)])
                    for decorator in node.decorator_list:
                        if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute):
                             if decorator.func.attr in ['get', 'post', 'put', 'delete', 'patch']:
                                for keyword in decorator.keywords:
                                    if keyword.arg == 'dependencies':
                                        if 'Depends' in ast.dump(keyword.value):
                                            has_auth = True

                    # Check function arguments (user: User = Depends(...))
                    for arg in node.args.args:
                        if arg.annotation:
                            ann_dump = ast.dump(arg.annotation)
                            if 'Depends' in ann_dump or 'Security' in ann_dump or 'get_current_user' in ann_dump:
                                has_auth = True

                    if not has_auth:
                        # Filter out public endpoints
                        public_keywords = ['login', 'health', 'public', 'docs', 'openapi', 'token']
                        if any(k in node.name.lower() for k in public_keywords) or 'public' in filepath:
                            continue

                        self.findings.append({
                            'type': 'Missing AuthZ',
                            'file': filepath,
                            'line': node.lineno,
                            'detail': f"Route '{http_method.upper()} {node.name}' might be missing authentication dependencies."
                        })


    def check_rate_limit(self, filepath, content):
        if 'janus/app/api' not in filepath:
            return

        sensitive_keywords = ['login', 'reset', 'password', 'signup', 'register', 'auth']
        is_sensitive_file = any(k in filepath.lower() for k in sensitive_keywords)

        if is_sensitive_file:
             if 'limiter' not in content and 'RateLimiter' not in content:
                 self.findings.append({
                     'type': 'Missing Rate Limit',
                     'file': filepath,
                     'line': 1,
                     'detail': "Sensitive endpoint file might be missing rate limiting logic."
                 })

    def check_vulnerabilities_python(self, filepath, content):
        risky_calls = ['eval', 'exec', 'subprocess.call', 'subprocess.Popen', 'yaml.load']
        for call in risky_calls:
            if f"{call}(" in content:
                 # simple check, ignores comments
                 line_num = content[:content.find(f"{call}(")].count('\n') + 1
                 self.findings.append({
                     'type': 'Potential Vulnerability',
                     'file': filepath,
                     'line': line_num,
                     'detail': f"Usage of '{call}' detected."
                 })

    def check_vulnerable_imports(self, filepath, content):
        # Check for known vulnerable packages or bad practices
        if 'import telnetlib' in content:
             self.findings.append({'type': 'Vulnerable Import', 'file': filepath, 'line': 1, 'detail': 'telnetlib is deprecated and insecure.'})
        if 'import xml.etree.ElementTree' in content and 'defusedxml' not in content:
             self.findings.append({'type': 'XML Vulnerability', 'file': filepath, 'line': 1, 'detail': 'Use defusedxml instead of xml.etree.ElementTree to prevent XXE.'})

    def report(self):
        if not self.findings:
            print("No significant issues found.")
            return

        # Sort findings by type and file
        self.findings.sort(key=lambda x: (x['type'], x['file'], x['line']))

        print(f"Found {len(self.findings)} issues:")
        print("=" * 40)

        current_type = ""
        for f in self.findings:
            if f['type'] != current_type:
                current_type = f['type']
                print(f"\n[{current_type}]")
                print("-" * len(f['type']))

            print(f"  File: {f['file']}:{f['line']}")
            print(f"  Detail: {f['detail']}")

if __name__ == "__main__":
    scanner = SecurityScanner(
        root_dirs=['janus', 'front/src'],
        exclude_dirs=['tests', 'test', 'node_modules', 'venv', '__pycache__', 'dist', 'build', '.git', 'migrations', 'scripts', 'docs'],
        exclude_files=['poetry.lock', 'package-lock.json', 'security_scan.py', 'test_scenario1_apis.py']
    )
    scanner.scan()
    scanner.report()
