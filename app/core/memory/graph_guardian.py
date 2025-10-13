"""
Graph Guardian - Sprint 8

"Guardião do Grafo" - Camada de normalização e validação para o grafo de conhecimento.
Garante consistência em nós (entidades) e relações, evitando poluição semântica.
"""

import logging
import re
from enum import Enum
from typing import Dict, Optional, Set

logger = logging.getLogger(__name__)


class RelationType(str, Enum):
    """Tipos de relações padronizados (schema fixo)."""

    # Relações de código
    CONTAINS = "CONTAINS"
    CALLS = "CALLS"
    IMPLEMENTS = "IMPLEMENTS"
    INHERITS_FROM = "INHERITS_FROM"
    DEPENDS_ON = "DEPENDS_ON"

    # Relações de conhecimento
    USES = "USES"
    RELATES_TO = "RELATES_TO"
    CAUSES = "CAUSES"
    SOLVES = "SOLVES"
    CAUSED_BY = "CAUSED_BY"
    SOLVED_BY = "SOLVED_BY"

    # Relações de experiência
    MENTIONS = "MENTIONS"
    EXTRACTED_FROM = "EXTRACTED_FROM"
    FOLLOWED_BY = "FOLLOWED_BY"

    # Relações semânticas
    IS_A = "IS_A"
    PART_OF = "PART_OF"
    HAS_PROPERTY = "HAS_PROPERTY"
    SIMILAR_TO = "SIMILAR_TO"


class EntityType(str, Enum):
    """Tipos de entidades padronizados."""

    # Código
    FILE = "File"
    FUNCTION = "Function"
    CLASS = "Class"
    MODULE = "Module"

    # Conhecimento
    CONCEPT = "Concept"
    TECHNOLOGY = "Technology"
    TOOL = "Tool"
    PATTERN = "Pattern"

    # Problemas e soluções
    ERROR = "Error"
    BUG = "Bug"
    SOLUTION = "Solution"
    WORKAROUND = "Workaround"

    # Pessoas e organização
    PERSON = "Person"
    TEAM = "Team"
    ORGANIZATION = "Organization"

    # Experiência
    EXPERIENCE = "Experience"


# Thesaurus: mapeamento de sinônimos para conceitos canônicos
ENTITY_SYNONYMS: Dict[str, str] = {
    # Erros
    "erro": "error",
    "erros": "error",
    "falha": "error",
    "falhas": "error",
    "bug": "bug",
    "bugs": "bug",
    "defeito": "bug",
    "defeitos": "bug",
    "problema": "error",
    "problemas": "error",
    "issue": "error",
    "issues": "error",

    # Soluções
    "solução": "solution",
    "soluções": "solution",
    "fix": "solution",
    "fixes": "solution",
    "correção": "solution",
    "correções": "solution",
    "resolução": "solution",

    # Agentes
    "agente": "agent",
    "agentes": "agent",
    "assistente": "agent",
    "assistentes": "agent",

    # Ferramentas
    "ferramenta": "tool",
    "ferramentas": "tool",
    "utilitário": "tool",
    "utilitários": "tool",

    # APIs
    "api": "api",
    "apis": "api",
    "endpoint": "endpoint",
    "endpoints": "endpoint",

    # Teste
    "teste": "test",
    "testes": "test",
    "testing": "test",

    # Performance
    "performance": "performance",
    "desempenho": "performance",
    "velocidade": "performance",
    "latência": "latency",
    "latencia": "latency",
}

# Mapeamento de tipos de relação alternativos para canônicos
RELATION_SYNONYMS: Dict[str, RelationType] = {
    "contem": RelationType.CONTAINS,
    "contém": RelationType.CONTAINS,
    "contains_value": RelationType.CONTAINS,
    "contem_com_valor": RelationType.CONTAINS,
    "has": RelationType.HAS_PROPERTY,
    "tem": RelationType.HAS_PROPERTY,

    "usa": RelationType.USES,
    "utiliza": RelationType.USES,
    "use": RelationType.USES,

    "relacionado_a": RelationType.RELATES_TO,
    "relaciona_com": RelationType.RELATES_TO,
    "related": RelationType.RELATES_TO,
    "related_to": RelationType.RELATES_TO,

    "causa": RelationType.CAUSES,
    "provoca": RelationType.CAUSES,
    "gera": RelationType.CAUSES,

    "resolve": RelationType.SOLVES,
    "soluciona": RelationType.SOLVES,
    "corrige": RelationType.SOLVES,

    "menciona": RelationType.MENTIONS,
    "cita": RelationType.MENTIONS,

    "seguido_por": RelationType.FOLLOWED_BY,
    "seguido_de": RelationType.FOLLOWED_BY,

    "depende_de": RelationType.DEPENDS_ON,
    "requer": RelationType.DEPENDS_ON,
    "requires": RelationType.DEPENDS_ON,

    "implementa": RelationType.IMPLEMENTS,
    "implements": RelationType.IMPLEMENTS,

    "chama": RelationType.CALLS,
    "invoca": RelationType.CALLS,
}


class GraphGuardian:
    """
    Guardião do Grafo: normaliza e valida entidades e relações antes de persistir no Neo4j.

    Responsabilidades:
    1. Normalização de nomes de entidades (lowercase, lematização, sinônimos)
    2. Padronização de tipos de entidades
    3. Validação e normalização de tipos de relações
    4. Garantia de consistência semântica
    """

    def __init__(self):
        self._lemma_cache: Dict[str, str] = {}
        self._validated_entities: Set[str] = set()

    def normalize_entity_name(self, name: str) -> str:
        """
        Normaliza o nome de uma entidade para forma canônica.

        Pipeline:
        1. Lowercase
        2. Trim e normalização de espaços
        3. Lematização simplificada (remoção de plurais básicos)
        4. Mapeamento de sinônimos

        Args:
            name: Nome original da entidade

        Returns:
            Nome normalizado
        """
        if not name or not isinstance(name, str):
            return ""

        # Cache check
        if name in self._lemma_cache:
            return self._lemma_cache[name]

        # 1. Lowercase e trim
        normalized = name.strip().lower()

        # 2. Remove caracteres especiais excessivos, mantém underscores e hífens
        normalized = re.sub(r'[^\w\s\-]', '', normalized)

        # 3. Normaliza múltiplos espaços para um único
        normalized = re.sub(r'\s+', ' ', normalized)

        # 4. Lematização simplificada (apenas para português e inglês básico)
        normalized = self._simple_lemmatize(normalized)

        # 5. Mapeia sinônimos para termos canônicos
        if normalized in ENTITY_SYNONYMS:
            normalized = ENTITY_SYNONYMS[normalized]

        # Cache result
        self._lemma_cache[name] = normalized

        return normalized

    def _simple_lemmatize(self, word: str) -> str:
        """
        Lematização simplificada sem biblioteca externa.
        Remove plurais básicos em português e inglês.
        """
        # Plural em português: remove 's' final se não for 'ss'
        if word.endswith('s') and not word.endswith('ss') and len(word) > 3:
            return word[:-1]

        # Plural em inglês: ies -> y
        if word.endswith('ies') and len(word) > 4:
            return word[:-3] + 'y'

        # Plural em inglês: es -> e (quando não é ação)
        if word.endswith('es') and len(word) > 3 and not word.endswith('ses'):
            return word[:-1]

        return word

    def normalize_entity_type(self, type_str: str) -> EntityType:
        """
        Normaliza e valida tipo de entidade.

        Args:
            type_str: Tipo sugerido pelo LLM

        Returns:
            EntityType válido do enum
        """
        if not type_str:
            return EntityType.CONCEPT

        # Normaliza para uppercase
        normalized = type_str.strip().upper()

        # Tenta match direto com enum
        for entity_type in EntityType:
            if entity_type.value.upper() == normalized or entity_type.name == normalized:
                return entity_type

        # Heurísticas para tipos comuns
        if any(x in normalized for x in ['ERR', 'FALHA', 'PROBLEM']):
            return EntityType.ERROR
        elif any(x in normalized for x in ['SOLU', 'FIX', 'CORREC']):
            return EntityType.SOLUTION
        elif any(x in normalized for x in ['TECH', 'TECNOLOG']):
            return EntityType.TECHNOLOGY
        elif any(x in normalized for x in ['TOOL', 'FERRAMENTA', 'UTIL']):
            return EntityType.TOOL
        elif any(x in normalized for x in ['FUNCTION', 'FUNC', 'METHOD']):
            return EntityType.FUNCTION
        elif any(x in normalized for x in ['CLASS', 'CLASSE']):
            return EntityType.CLASS
        elif any(x in normalized for x in ['FILE', 'ARQUIVO']):
            return EntityType.FILE
        elif any(x in normalized for x in ['PERSON', 'PESSOA', 'USER', 'USUARIO']):
            return EntityType.PERSON

        # Default: Concept (mais genérico)
        logger.debug(f"Tipo '{type_str}' não reconhecido. Usando CONCEPT como padrão.")
        return EntityType.CONCEPT

    def normalize_relation_type(self, type_str: str) -> Optional[RelationType]:
        """
        Normaliza e valida tipo de relação.

        Args:
            type_str: Tipo sugerido pelo LLM

        Returns:
            RelationType válido do enum ou None se inválido
        """
        if not type_str:
            return None

        # Normaliza para lowercase para comparação
        normalized_lower = type_str.strip().lower()
        normalized_upper = type_str.strip().upper()

        # Tenta match direto com enum (case-insensitive)
        for rel_type in RelationType:
            if rel_type.value.upper() == normalized_upper or rel_type.name == normalized_upper:
                return rel_type

        # Tenta sinônimos
        if normalized_lower in RELATION_SYNONYMS:
            return RELATION_SYNONYMS[normalized_lower]

        # Limpa underscores e hífens para match flexível
        clean = normalized_lower.replace('_', '').replace('-', '').replace(' ', '')
        for syn_key, rel_type in RELATION_SYNONYMS.items():
            if clean == syn_key.replace('_', '').replace('-', '').replace(' ', ''):
                return rel_type

        # Se não encontrou, retorna RELATES_TO como fallback genérico
        logger.warning(
            f"Tipo de relação '{type_str}' não reconhecido. "
            f"Usando RELATES_TO como fallback. Considere adicionar ao enum."
        )
        return RelationType.RELATES_TO

    def validate_and_normalize_entity(
            self,
            name: str,
            entity_type: str,
            properties: Optional[Dict] = None
    ) -> Dict[str, any]:
        """
        Valida e normaliza uma entidade completa.

        Args:
            name: Nome da entidade
            entity_type: Tipo da entidade
            properties: Propriedades adicionais

        Returns:
            Dicionário com entidade normalizada
        """
        normalized_name = self.normalize_entity_name(name)
        validated_type = self.normalize_entity_type(entity_type)

        if not normalized_name:
            raise ValueError(f"Nome de entidade inválido após normalização: '{name}'")

        return {
            "name": normalized_name,
            "type": validated_type.value,
            "properties": properties or {},
            "original_name": name,  # Mantém original para debug
        }

    def validate_and_normalize_relationship(
            self,
            from_entity: str,
            to_entity: str,
            rel_type: str,
            properties: Optional[Dict] = None
    ) -> Optional[Dict[str, any]]:
        """
        Valida e normaliza um relacionamento completo.

        Args:
            from_entity: Nome da entidade origem
            to_entity: Nome da entidade destino
            rel_type: Tipo da relação
            properties: Propriedades adicionais

        Returns:
            Dicionário com relacionamento normalizado ou None se inválido
        """
        normalized_from = self.normalize_entity_name(from_entity)
        normalized_to = self.normalize_entity_name(to_entity)
        validated_rel_type = self.normalize_relation_type(rel_type)

        if not normalized_from or not normalized_to:
            logger.warning(
                f"Relacionamento ignorado: entidade origem/destino vazia após normalização. "
                f"Original: '{from_entity}' -> '{to_entity}'"
            )
            return None

        if not validated_rel_type:
            logger.warning(
                f"Relacionamento ignorado: tipo de relação inválido '{rel_type}'"
            )
            return None

        return {
            "from": normalized_from,
            "to": normalized_to,
            "type": validated_rel_type.value,
            "properties": properties or {},
            "original_from": from_entity,
            "original_to": to_entity,
        }


# Instância global do guardião
graph_guardian = GraphGuardian()
