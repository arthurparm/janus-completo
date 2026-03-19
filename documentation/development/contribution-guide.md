# Contribution Guide - Janus Completo

## Objetivo
Guia centralizado para contribuições no projeto Janus, cobrindo frontend, backend e documentação.

## Escopo
- **Inclui**: Fluxo de contribuição, convenções, padrões de código, checklist de qualidade
- **Exclui**: Detalhes de negócio (ver documentação específica por área)
- **Público-alvo**: Todos os contribuidores do projeto

## Fluxo de Contribuição

### 1. Preparação
```bash
# 1. Fork e clone
git clone https://github.com/seu-usuario/janus-completo.git
cd janus-completo

# 2. Setup do ambiente
python tooling/dev.py up  # Recomendado: setup completo

# 3. Criar branch
git checkout -b feature/nova-funcionalidade
# ou: git checkout -b fix/correcao-bug
```

### 2. Desenvolvimento

#### Frontend (Angular)
```bash
cd frontend
npm install
npm start  # http://localhost:4200

# Em outro terminal - qualidade
cd frontend
npm run lint
npm run test
npm run build
```

#### Backend (FastAPI)
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Em outro terminal - qualidade
cd backend
pytest
ruff check .
mypy app/
```

### 3. Convenções de Código

#### Commits - Conventional Commits
```
<tipo>(escopo opcional): descrição breve

[corpo opcional]

[rodapé opcional]
```

**Tipos permitidos:**
- `feat`: Nova funcionalidade
- `fix`: Correção de bug
- `docs`: Documentação
- `style`: Formatação (sem mudança de lógica)
- `refactor`: Refatoração sem mudança de comportamento
- `test`: Adição/correção de testes
- `build`: Mudanças em build system
- `ci`: Mudanças em CI/CD
- `chore`: Atualizações de dependências
- `perf`: Melhorias de performance
- `revert`: Reversão de commits anteriores

**Exemplos:**
```bash
git commit -m "feat(chat): adicionar streaming de mensagens"
git commit -m "fix(api): corrigir timeout em requisições longas"
git commit -m "docs(readme): atualizar instruções de setup"
```

#### Nomenclatura de Branches
```
feature/nome-da-funcionalidade
fix/descricao-do-bug
hotfix/correcao-urgente
docs/atualizacao-documentacao
refactor/melhoria-codigo
test/adicionar-testes
```

#### Frontend Específico
- **Componentes**: PascalCase (`UserCardComponent`)
- **Serviços**: PascalCase + suffix `Service` (`UserService`)
- **Métodos**: camelCase (`getUserData()`)
- **Constantes**: UPPER_SNAKE_CASE (`API_BASE_URL`)
- **Arquivos**: kebab-case (`user-card.component.ts`)

#### Backend Específico
- **Classes**: PascalCase (`UserRepository`)
- **Funções**: snake_case (`get_user_by_id()`)
- **Constantes**: UPPER_SNAKE_CASE (`MAX_RETRY_COUNT`)
- **Arquivos**: snake_case (`user_repository.py`)

### 4. Checklist de Qualidade

#### Antes de Commitar
- [ ] Código segue convenções do projeto
- [ ] Testes passam localmente
- [ ] Lint sem erros
- [ ] Build gera sem warnings
- [ ] Documentação atualizada (se aplicável)

#### Frontend Checklist
```bash
cd frontend
npm run lint        # Sem erros
npm run lint:fix    # Auto-fix aplicado
npm run test        # Todos passam
npm run build       # Build de produção ok
```

#### Backend Checklist
```bash
cd backend
ruff check .        # Sem erros de lint
pytest              # Todos testes passam
mypy app/           # Sem erros de tipo
```

#### Documentação
- [ ] README atualizado (se necessário)
- [ ] Comentários em código complexo
- [ ] JSDoc/TSDoc para funções públicas
- [ ] Docstrings Python para funções públicas

### 5. Pull Request

#### Template de PR
Use o template em `.github/pull_request_template.md` e inclua:

1. **Descrição clara** do que foi mudado
2. **Motivação** para a mudança
3. **Testes realizados** (com screenshots se UI)
4. **Breaking changes** (se houver)
5. **Checklist de qualidade** preenchido

#### Exemplo de Descrição de PR
```markdown
## Descrição
Adiciona funcionalidade de exportação de dados em CSV para relatórios.

## Motivação
Usuários solicitaram forma fácil de exportar dados para Excel.

## Mudanças
- Adiciona botão "Exportar CSV" na tela de relatórios
- Implementa serviço `DataExportService`
- Adiciona testes unitários e de integração

## Testes
- [ ] Teste unitário: conversão de dados para CSV
- [ ] Teste de integração: download via API
- [ ] Teste manual: verificação de arquivo gerado

## Screenshots
[Incluir screenshots da nova funcionalidade]

## Breaking Changes
Nenhum

## Checklist
- [ ] Lint passando
- [ ] Testes passando
- [ ] Documentação atualizada
- [ ] CHANGELOG atualizado
```

### 6. Revisão de Código

#### Como Revisor
1. **Seja construtivo** - Sugira melhorias, não apenas aponte problemas
2. **Teste localmente** - Rodar código quando possível
3. **Verifique edge cases** - Pense em casos não cobertos
4. **Documentação** - Garanta que está clara
5. **Performance** - Considere impacto de performance

#### Como Autor
1. **Responda comentários** - Address todas as preocupações
2. **Faça mudanças solicitadas** - Ou justifique por que não
3. **Atualize branch** - Mantenha sincronizado com main
4. **Teste novamente** - Após mudanças significativas

### 7. Merge e Deploy

#### Critérios para Merge
- [ ] Aprovado por pelo menos 1 revisor
- [ ] CI/CD pipeline passando
- [ ] Sem conflitos com main branch
- [ ] Documentação completa

#### Após Merge
1. **Delete branch** remota: `git push origin --delete feature/branch`
2. **Atualize local**: `git fetch --prune`
3. **Acompanhe deploy** (se aplicável)
4. **Monitore métricas** (se aplicável)

## Recursos Úteis

### Comandos de Diagnóstico
```bash
# Verificar setup completo
python tooling/dev.py doctor

# Logs de todos os serviços
docker compose -f docker-compose.pc1.yml --env-file .env.pc1 logs
docker compose -f docker-compose.pc2.yml --env-file .env.pc2 logs

# Testar API
curl -sf http://localhost:8000/health
```

### Documentação Específica
- [Frontend Guide](../development-guide-frontend.md)
- [Backend Guide](../development-guide-backend.md)
- [Testing Guide](../testing-guide.md)
- [API Documentation](../api/overview.md)

### Links Externos
- [Conventional Commits](https://www.conventionalcommits.org/)
- [Angular Style Guide](https://angular.io/guide/styleguide)
- [PEP 8 - Python Style Guide](https://www.python.org/dev/peps/pep-0008/)
- [FastAPI Best Practices](https://fastapi.tiangolo.com/tutorial/bigger-applications/)

## Última Atualização
2026-03-11 - Consolidado de frontend/CONTRIBUTING.md e documentation/contribution-guide.md