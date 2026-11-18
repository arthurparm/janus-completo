#!/usr/bin/env bash
set -euo pipefail
# Run the tail of a pipeline in the current shell (not a subshell) so that
# counters updated inside `... | while read; do ...; done` loops below are
# visible in the final report instead of being lost when the subshell exits.
shopt -s lastpipe

# Script para verificação de qualidade da documentação
# Uso: ./scripts/docs-check.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

echo "🔍 Verificando qualidade da documentação..."

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Contadores
ERRORS=0
WARNINGS=0

# Função para imprimir erro
error() {
    echo -e "${RED}❌ ERRO: $1${NC}" >&2
    ERRORS=$((ERRORS + 1))
}

# Função para imprimir aviso
warning() {
    echo -e "${YELLOW}⚠️  AVISO: $1${NC}" >&2
    WARNINGS=$((WARNINGS + 1))
}

# Função para imprimir sucesso
success() {
    echo -e "${GREEN}✅ $1${NC}"
}

# Verificar se arquivos de documentação existem
echo "📁 Verificando estrutura de documentação..."

REQUIRED_FILES=(
    "README.md"
    "AGENTS.md"
    "CODEBASE_MAP.md"
    "BACKEND_RUNTIME.md"
    "FRONTEND_ANGULAR.md"
    "OPS_QA.md"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [[ -f "$ROOT_DIR/$file" ]]; then
        success "Arquivo encontrado: $file"
    else
        error "Arquivo ausente: $file"
    fi
done

# Verificar links quebrados (versão simplificada)
echo "🔗 Verificando links internos..."
cd "$ROOT_DIR"

# Verificar apenas links simples para evitar erros de regex
find documentation -name "*.md" -type f | while read -r file; do
    # Procurar por links relativos simples
    { grep -oE '\]\([^http][^)]*\)' "$file" 2>/dev/null || true; } | while read -r link_match; do
        # Extrair apenas o caminho do link
        link=$(echo "$link_match" | sed 's/.*](\([^)]*\)).*/\1/')
        
        # Ignorar links externos, âncoras e links vazios
        if [[ "$link" =~ ^http ]] || [[ "$link" =~ ^# ]] || [[ -z "$link" ]]; then
            continue
        fi

        # Descartar fragmento (#anchor, #L10-L20) antes de checar o arquivo alvo
        link_path="${link%%#*}"
        if [[ -z "$link_path" ]]; then
            continue
        fi

        # Resolver caminho relativo normalizando ".."/"." de verdade (realpath -m
        # aceita alvos inexistentes, só normaliza o caminho para checarmos depois)
        link_dir="$(dirname "$file")"
        target="$(realpath -m "$link_dir/$link_path")"

        # Verificar se o alvo existe
        if [[ ! -f "$target" ]] && [[ ! -d "$target" ]]; then
            error "Link quebrado em $file: $link"
        fi
    done
done

# Verificar headers obrigatórios (versão simplificada)
echo "📋 Verificando estrutura dos documentos..."

# Verificar se os documentos têm conteúdo básico
for file in "${REQUIRED_FILES[@]}"; do
    if [[ -f "$ROOT_DIR/$file" ]]; then
        content=$(cat "$ROOT_DIR/$file")
        
        # Verificar tamanho mínimo
        if [[ ${#content} -lt 100 ]]; then
            warning "Documento muito curto: $file"
        fi
        
        # Verificar se tem headers
        if ! echo "$content" | grep -q "^#"; then
            warning "Sem headers principais em: $file"
        fi
    fi
done

# Verificar data de atualização
echo "📅 Verificando datas de atualização..."

find documentation -name "*.md" -type f -mtime +90 | while read -r file; do
    warning "Documentação desatualizada (>90 dias): $file"
done

# Verificar exemplos de código
echo "💻 Verificando exemplos de código..."

find documentation -name "*.md" -type f | while read -r file; do
    # Contar blocos de código
    code_blocks=$(grep -c '^```' "$file" 2>/dev/null || true)
    
    if [[ $code_blocks -lt 2 ]]; then
        warning "Poucos exemplos de código em: $file ($code_blocks blocos)"
    fi
done

# Verificar tamanho dos arquivos
echo "📊 Verificando tamanho dos documentos..."

find documentation -name "*.md" -type f -size +100k | while read -r file; do
    warning "Documento muito grande: $file ($(du -h "$file" | cut -f1))"
done

# Relatório final
echo ""
echo "📈 Relatório de Qualidade da Documentação"
echo "========================================="
echo "Arquivos verificados: $(find documentation -name "*.md" -type f | wc -l)"
echo "Erros encontrados: $ERRORS"
echo "Avisos encontrados: $WARNINGS"
echo ""

if [[ $ERRORS -eq 0 ]] && [[ $WARNINGS -eq 0 ]]; then
    success "Documentação em excelente estado! 🎉"
    exit 0
elif [[ $ERRORS -eq 0 ]]; then
    warning "Documentação OK, mas há avisos para resolver."
    exit 0
else
    error "Documentação precisa de atenção. Por favor, corrija os erros acima."
    exit 1
fi