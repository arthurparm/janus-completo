from __future__ import annotations

import asyncio
import json

from app.db import db
from app.services.db_migration_service import DBMigrationService


async def main() -> None:
    await db.create_tables()
    result = DBMigrationService().migrate_schema()
    print(json.dumps(result, sort_keys=True))
    await db.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
