import urllib.request
import urllib.error
from html.parser import HTMLParser
import sys

# --- Helper for HTML Stripping (Copied from agent_tools.py) ---
class MLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.reset()
        self.strict = False
        self.convert_charrefs = True
        self.text = []

    def handle_data(self, d):
        self.text.append(d)

    def get_data(self):
        return "".join(self.text)

def strip_tags(html):
    try:
        s = MLStripper()
        s.feed(html)
        return s.get_data()
    except Exception:
        return html

def browse_url(url: str) -> str:
    print(f"[TEST] Navegando para: {url}")
    
    if not url.startswith("http"):
        return "Erro: A URL deve começar com http:// ou https://"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as response:
            print(f"[TEST] Status Code: {response.getcode()}")
            charset = response.headers.get_content_charset() or 'utf-8'
            html_content = response.read().decode(charset, errors='replace')
            print(f"[TEST] HTML baixado ({len(html_content)} bytes). Extraindo texto...")
            
            # Extrair texto limpo
            text_content = strip_tags(html_content)
            
            # Limpeza básica de white-space
            text_content = "\n".join([line.strip() for line in text_content.splitlines() if line.strip()])
            
            return text_content[:20000] 
            
    except urllib.error.HTTPError as e:
        return f"Erro HTTP {e.code}: {e.reason}"
    except urllib.error.URLError as e:
        return f"Erro de Conexão: {e.reason}"
    except Exception as e:
        return f"Erro inesperado ao acessar URL: {e}"

if __name__ == "__main__":
    url = "https://example.com"
    print(f"--- Iniciando Teste do Navegador: {url} ---")
    result = browse_url(url)
    print("-" * 40)
    print("CONTEÚDO EXTRAÍDO:")
    print(result)
    print("-" * 40)
    if "Example Domain" in result:
        print("✅ SUCESSO: Conteúdo esperado encontrado!")
    else:
        print("❌ FALHA: Conteúdo esperado não encontrado.")
