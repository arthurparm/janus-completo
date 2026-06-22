---
tipo: codigo
dominio: backend
camada: services
gerado: true
origem: "backend/app/services/db_migration_service.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# db_migration_service

## Arquivos-fonte
- `backend/app/services/db_migration_service.py`

## Fluxos de uso (chamadores)
- `backend/app/api/v1/endpoints/system_status.py`
- `backend/app/core/kernel.py`

## Símbolos
- class: `DBMigrationService`
- method: `DBMigrationService._get_session(self)` -> `Session`
- method: `DBMigrationService._execute_ddl(self, s: Session, sql: str, change_id: str, applied: list[str])` -> `None`
- method: `DBMigrationService._index_exists(self, s: Session, table: str, index_name: str)` -> `bool`
- method: `DBMigrationService._constraint_exists(self, s: Session, table: str, constraint_name: str)` -> `bool`
- method: `DBMigrationService._column_exists(self, s: Session, table: str, column: str)` -> `bool`
- method: `DBMigrationService._table_exists(self, s: Session, table: str)` -> `bool`
- method: `DBMigrationService._dialect_name(self, s: Session)` -> `str`
- method: `DBMigrationService._unique_constraint_sql(self, *, dialect: str, table: str, constraint: str, columns_csv: str)` -> `str`
- method: `DBMigrationService._message_json_column_sql(self, *, dialect: str, column: str)` -> `str`
- method: `DBMigrationService._knowledge_spaces_table_sql(self, *, dialect: str)` -> `str`
- method: `DBMigrationService.validate_schema(self)` -> `dict[str, Any]`
- method: `DBMigrationService.migrate_schema(self)` -> `dict[str, Any]`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
