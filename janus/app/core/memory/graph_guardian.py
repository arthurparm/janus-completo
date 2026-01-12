"""
Graph Guardian - Sprint 8

"Guardião do Grafo" - Camada de normalização e validação para o grafo de conhecimento.
Garante consistência em nós (entidades) e relações, evitando poluição semântica.
"""

import logging
import re
from enum import Enum

from app.core.memory.semantic_relation_matcher import match_relation_type as match_semantic_relation

logger = logging.getLogger(__name__)


class RelationType(str, Enum):
    """Tipos de relações padronizados (schema fixo)."""

    # Relações de código
    CONTAINS = "CONTAINS"
    CALLS = "CALLS"
    IMPLEMENTS = "IMPLEMENTS"
    INHERITS_FROM = "INHERITS_FROM"
    DEPENDS_ON = "DEPENDS_ON"
    CREATES = "CREATES"
    RETURNS = "RETURNS"
    INCLUDES = "INCLUDES"

    # Relações de conhecimento
    USES = "USES"
    RELATES_TO = "RELATES_TO"
    CAUSES = "CAUSES"
    SOLVES = "SOLVES"
    CAUSED_BY = "CAUSED_BY"
    SOLVED_BY = "SOLVED_BY"
    CACHES = "CACHES"
    APPLIED_TO = "APPLIED_TO"
    INTERACTS_WITH = "INTERACTS_WITH"
    HAS_MODEL = "HAS_MODEL"

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
ENTITY_SYNONYMS: dict[str, str] = {
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
RELATION_SYNONYMS: dict[str, RelationType] = {
    "contem": RelationType.CONTAINS,
    "contém": RelationType.CONTAINS,
    "contains_value": RelationType.CONTAINS,
    "contem_com_valor": RelationType.CONTAINS,
    "contains": RelationType.CONTAINS,
    "has": RelationType.HAS_PROPERTY,
    "tem": RelationType.HAS_PROPERTY,
    "has_property": RelationType.HAS_PROPERTY,
    "has_metadata": RelationType.HAS_PROPERTY,
    "has_result": RelationType.HAS_PROPERTY,
    "has_position": RelationType.HAS_PROPERTY,
    "optimized_for": RelationType.HAS_PROPERTY,
    "usa": RelationType.USES,
    "utiliza": RelationType.USES,
    "use": RelationType.USES,
    "uses": RelationType.USES,
    "accesses": RelationType.USES,
    "retrieves": RelationType.USES,
    "relacionado_a": RelationType.RELATES_TO,
    "relaciona_com": RelationType.RELATES_TO,
    "related": RelationType.RELATES_TO,
    "related_to": RelationType.RELATES_TO,
    "identifies": RelationType.RELATES_TO,
    "detects": RelationType.RELATES_TO,
    "investigates": RelationType.RELATES_TO,
    "analyzes": RelationType.RELATES_TO,
    "evaluates": RelationType.RELATES_TO,
    "explains": RelationType.RELATES_TO,
    "summarizes": RelationType.RELATES_TO,
    "proposes": RelationType.RELATES_TO,
    "provides": RelationType.RELATES_TO,
    "provides_details_for": RelationType.RELATES_TO,
    "interpreted_as": RelationType.RELATES_TO,
    "targets": RelationType.RELATES_TO,
    "defines": RelationType.RELATES_TO,
    "restricts": RelationType.RELATES_TO,
    "should_do": RelationType.RELATES_TO,
    "should_not_do": RelationType.RELATES_TO,
    "should_maintain": RelationType.RELATES_TO,
    "demonstrates": RelationType.RELATES_TO,
    "reflects": RelationType.RELATES_TO,
    "does_not_reflect": RelationType.RELATES_TO,
    "calculated_from": RelationType.RELATES_TO,
    "calculated_using": RelationType.RELATES_TO,
    "achieves": RelationType.RELATES_TO,
    "causa": RelationType.CAUSES,
    "provoca": RelationType.CAUSES,
    "gera": RelationType.CAUSES,
    "leads_to": RelationType.CAUSES,
    "results_in": RelationType.CAUSES,
    "generates": RelationType.CAUSES,
    "generated": RelationType.CAUSES,
    "initiates": RelationType.CAUSES,
    "result_of": RelationType.CAUSED_BY,
    "initiated": RelationType.CAUSED_BY,
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
    "is": RelationType.IS_A,
    "part_of": RelationType.PART_OF,
    # New relationship types
    "creates": RelationType.CREATES,
    "cria": RelationType.CREATES,
    "produces": RelationType.CREATES,
    "builds": RelationType.CREATES,
    "returns": RelationType.RETURNS,
    "retorna": RelationType.RETURNS,
    "outputs": RelationType.RETURNS,
    "includes": RelationType.INCLUDES,
    "inclui": RelationType.INCLUDES,
    "incorporates": RelationType.INCLUDES,
    "caches": RelationType.CACHES,
    "armazena_cache": RelationType.CACHES,
    "stores": RelationType.CACHES,
    "applied_to": RelationType.APPLIED_TO,
    "aplicado_a": RelationType.APPLIED_TO,
    "applies_to": RelationType.APPLIED_TO,
    "interacts_with": RelationType.INTERACTS_WITH,
    "interage_com": RelationType.INTERACTS_WITH,
    "communicates_with": RelationType.INTERACTS_WITH,
    "has_model": RelationType.HAS_MODEL,
    "tem_modelo": RelationType.HAS_MODEL,
    "uses_model": RelationType.HAS_MODEL,
}

ENTITY_PROPERTY_SYNONYMS: dict[str, dict[str, list[str]]] = {
    EntityType.TOOL.value: {
        "description": ["descricao", "descrição"],
        "purpose": ["finalidade", "proposito", "propósito"],
        "category": ["categoria", "categoria_solicitada"],
        "permission_level": ["nivel_permissao", "nivel_permissao_solicitado"],
    },
    EntityType.CONCEPT.value: {
        "description": ["descricao", "descrição"],
        "purpose": ["finalidade"],
        "category": ["categoria"],
    },
    EntityType.FUNCTION.value: {
        "description": ["descricao", "descrição"],
        "parameter": ["parametro"],
        "output": ["retorno"],
    },
    EntityType.ERROR.value: {
        "description": ["descricao", "descrição"],
        "category": ["categoria"],
        "context": ["contexto"],
    },
    EntityType.PATTERN.value: {
        "description": ["descricao", "descrição"],
        "purpose": ["proposito", "propósito"],
        "category": ["categoria"],
        "context": ["contexto"],
    },
    EntityType.SOLUTION.value: {
        "description": ["descricao", "descrição"],
        "category": ["categoria"],
        "approach": ["abordagem"],
    },
    EntityType.TECHNOLOGY.value: {
        "description": ["descricao", "descrição"],
        "category": ["categoria"],
        "context": ["contexto"],
        "purpose": ["finalidade"],
    },
    EntityType.PERSON.value: {
        "role": ["papel", "funcao", "função"],
    },
}


class GraphGuardian:
    """
    Guardião do Grafo: normaliza e valida entidades e relações antes de persistir no Neo4j.

    Responsabilidades:
    - Normalizar tipos de entidades (classes, funções, erros, conceitos)
    - Normalizar tipos de relação (verificar enum, sinônimos, semântica)
    - Prevenir explosão de tipos de relações desconhecidas
    - Lematizar nomes (singular/plural)
    """

    def __init__(self):
        self._lemma_cache: dict[str, str] = {}
        self._validated_entities: set[str] = set()

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
        normalized = re.sub(r"[^\w\s\-]", "", normalized)

        # 3. Normaliza múltiplos espaços para um único
        normalized = re.sub(r"\s+", " ", normalized)

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
        if word.endswith("s") and not word.endswith("ss") and len(word) > 3:
            return word[:-1]

        # Plural em inglês: ies -> y
        if word.endswith("ies") and len(word) > 4:
            return word[:-3] + "y"

        # Plural em inglês: es -> e (quando não é ação)
        if word.endswith("es") and len(word) > 3 and not word.endswith("ses"):
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
        if any(x in normalized for x in ["ERR", "FALHA", "PROBLEM"]):
            return EntityType.ERROR
        elif any(x in normalized for x in ["SOLU", "FIX", "CORREC"]):
            return EntityType.SOLUTION
        elif any(x in normalized for x in ["TECH", "TECNOLOG"]):
            return EntityType.TECHNOLOGY
        elif any(x in normalized for x in ["TOOL", "FERRAMENTA", "UTIL"]):
            return EntityType.TOOL
        elif any(x in normalized for x in ["FUNCTION", "FUNC", "METHOD"]):
            return EntityType.FUNCTION
        elif any(x in normalized for x in ["CLASS", "CLASSE"]):
            return EntityType.CLASS
        elif any(x in normalized for x in ["FILE", "ARQUIVO"]):
            return EntityType.FILE
        elif any(x in normalized for x in ["PERSON", "PESSOA", "USER", "USUARIO"]):
            return EntityType.PERSON

        # Default: Concept (mais genérico)
        logger.debug(f"Tipo '{type_str}' não reconhecido. Usando CONCEPT como padrão.")
        return EntityType.CONCEPT

    def normalize_relation_type(self, type_str: str) -> RelationType | None:
        """
        Normaliza e valida tipo de relação.

        Args:
            type_str: Tipo sugerido pelo LLM

        Returns:
            RelationType válido do enum ou None se inválido
        """
        if not type_str:
            return None

        # Tenta match semântico (cobre enum, sinônimos e fuzzy logic)
        matched_enum, score = match_semantic_relation(type_str)

        # Convert to local Enum by value
        try:
            return RelationType(matched_enum.value)
        except ValueError:
            # Se o valor retornado pelo matcher não existir no enum local, fallback
            logger.warning(
                f"Relation type mismatch: {matched_enum.value} not in GraphGuardian.RelationType. Fallback to RELATES_TO."
            )
            return RelationType.RELATES_TO

    def _normalize_properties(self, entity_type: EntityType, properties: dict | None) -> dict:
        props = dict(properties or {})
        mapping = ENTITY_PROPERTY_SYNONYMS.get(entity_type.value)
        if not mapping:
            return props
        for canonical, synonyms in mapping.items():
            if canonical not in props:
                for synonym in synonyms:
                    if synonym in props and props[synonym] not in (None, ""):
                        props[canonical] = props[synonym]
                        break
            for synonym in synonyms:
                if synonym in props:
                    props.pop(synonym, None)
        return props

    def validate_and_normalize_entity(
        self, name: str, entity_type: str, properties: dict | None = None
    ) -> dict[str, any]:
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

        if properties is None:
            normalized_properties = {}
        else:
            normalized_properties = self._normalize_properties(validated_type, properties)

        if not normalized_name:
            raise ValueError(f"Nome de entidade inválido após normalização: '{name}'")

        return {
            "name": normalized_name,
            "type": validated_type.value,
            "properties": normalized_properties,
            "original_name": name,  # Mantém original para debug
        }

    def validate_and_normalize_relationship(
        self, from_entity: str, to_entity: str, rel_type: str, properties: dict | None = None
    ) -> dict[str, any] | None:
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
            logger.warning(f"Relacionamento ignorado: tipo de relação inválido '{rel_type}'")
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
