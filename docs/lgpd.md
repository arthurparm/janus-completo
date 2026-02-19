# Relatório de Conformidade LGPD (Lei Geral de Proteção de Dados)

**Data da Auditoria:** 12/02/2026
**Auditor:** Jules (AI Assistant)

## Resumo

Este documento lista os pontos de coleta de dados pessoais, lacunas de conformidade e recomendações para garantir o cumprimento da LGPD. O sistema coleta dados como e-mail, telefone, CPF e voz do usuário.

## Pontos de Coleta de Dados Pessoais

### 1. Cadastro e Login (`janus/app/api/v1/endpoints/auth.py`)
- **Dados Coletados:**
    - `email`: Obrigatório para cadastro e login.
    - `phone`: Opcional no cadastro.
    - `cpf`: Opcional no cadastro.
    - `full_name`: Obrigatório no cadastro.
- **Base Legal:** Execução de contrato (Termos de Uso) e consentimento.
- **Armazenamento:** Banco de dados relacional (Postgres). Senhas são hashadas.

### 2. Comandos de Voz (`janus/app/interfaces/daemon/daemon.py`)
- **Dados Coletados:**
    - `voice_command`: O comando transcrito pode conter dados pessoais sensíveis ditados pelo usuário.
- **Base Legal:** Legítimo interesse (execução do comando) e consentimento (ativação do daemon).
- **Armazenamento:** Logs do sistema (temporário) e potencialmente no histórico de conversas (Qdrant/Neo4j).

## Lacunas de Conformidade (Gaps)

### 1. Consentimento Granular Insuficiente
**Risco:** Médio
**Detalhes:**
- O cadastro possui apenas um campo `terms` booleano. Não há opções separadas para consentimento de marketing, uso de dados para treinamento de IA ou compartilhamento com terceiros.
- Não há registro auditável detalhado de *quando* e *quais* termos específicos foram aceitos, apenas o status final.

### 2. Retenção de Dados e "Direito ao Esquecimento"
**Risco:** Médio/Alto
**Detalhes:**
- Não existe um processo automatizado ou endpoint claro para que o usuário solicite a exclusão completa de seus dados (Direito de Exclusão).
- Logs do daemon (`logger.info`) podem reter dados pessoais indefinidamente dependendo da política de rotação de logs do servidor.
- Dados vetorizados (Qdrant) e no grafo (Neo4j) podem persistir fragmentos de conversas antigas mesmo após a exclusão da conta se não houver um processo de "cascade delete" robusto.

### 3. Exposição Acidental em Logs
**Risco:** Baixo
**Detalhes:**
- O daemon loga o comando transcrito na íntegra. Se o usuário ditar "minha senha do banco é 1234", isso será logado em texto plano.

## Checklist de Conformidade

- [ ] **Mapeamento:** Todos os novos campos de dados pessoais foram mapeados neste documento?
- [ ] **Consentimento:** O usuário deu consentimento explícito para cada finalidade de uso dos dados?
- [ ] **Minimização:** Estamos coletando apenas os dados estritamente necessários?
- [ ] **Segurança:** Os dados em repouso e em trânsito estão criptografados?
- [ ] **Direitos do Titular:** Existe um canal funcional para o usuário solicitar acesso, correção ou exclusão de seus dados?
- [ ] **Retenção:** Existe uma política clara de expurgo de dados antigos ou desnecessários?

## Recomendações Acionáveis

1.  **Implementar Consentimento Granular:** Adicionar tabela de `user_consents` para registrar aceites individuais (termos, marketing, IA training) com timestamp e versão do documento.
2.  **Mascaramento de PII em Logs:** Utilizar bibliotecas (como `presidio-analyzer` ou filtros de regex) para detectar e mascarar dados sensíveis (CPF, e-mail, padrões numéricos de cartão) antes de logar comandos de voz.
3.  **Endpoint de Exclusão (Right to be Forgotten):** Criar um endpoint `DELETE /api/v1/users/me` que remove não apenas o registro no Postgres, mas também limpa vetores no Qdrant e nós no Neo4j associados ao `user_id`.
4.  **Política de Retenção de Logs:** Configurar rotação de logs para garantir que dados de depuração não sejam mantidos por mais tempo do que o necessário (ex: 30 dias).
5.  **Aviso de Privacidade:** Atualizar a interface do frontend para exibir links claros para a Política de Privacidade e Termos de Uso no momento do cadastro.

---
*Este documento deve ser revisado sempre que houver alterações no modelo de dados ou nos fluxos de coleta de informações.*
