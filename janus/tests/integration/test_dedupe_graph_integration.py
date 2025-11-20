import asyncio
import time
import pytest

from app.db.graph import get_graph_db
from app.repositories.knowledge_repository import KnowledgeRepository
from app.models.schemas import GraphRelationship


async def _create_min_graph(db):
    async with await db.get_session() as session:
        tx = await session.begin_transaction()
        await tx.run("MERGE (:Concept {name: 'A'})")
        await tx.run("MERGE (:Concept {name: 'A'})")
        await tx.run("MERGE (:Concept {name: 'B'})")
        await tx.run("MERGE (:Concept {name: 'C'})")
        await tx.run("MATCH (a:Concept {name:'A'}), (b:Concept {name:'B'}) MERGE (a)-[:RELATES_TO {w:1}]->(b)")
        await tx.run("MATCH (a:Concept {name:'A'}), (b:Concept {name:'B'}) MERGE (a)-[:RELATES_TO {w:1}]->(b)")
        await tx.commit()


@pytest.mark.asyncio
async def test_dedupe_concepts_integration():
    db = await get_graph_db()
    if not await db.health_check():
        pytest.skip("neo4j offline")
    await _create_min_graph(db)
    repo = KnowledgeRepository(db)
    t0 = time.time()
    res = await repo.dedupe_concepts()
    elapsed = time.time() - t0
    assert elapsed < 0.5
    if elapsed > 0.3:
        pytest.warns(UserWarning)
    rows = await db.query("MATCH (c:Concept) RETURN c.name as name, count(c) as cnt ORDER BY name")
    by_name = {r["name"]: r["cnt"] for r in rows}
    assert by_name.get("A", 0) == 1
    assert by_name.get("B", 0) == 1
    assert by_name.get("C", 0) == 1
    rels = await db.query("MATCH ()-[r:RELATES_TO]->() RETURN count(r) as cnt")
    assert rels[0]["cnt"] == 1


@pytest.mark.asyncio
async def test_dedupe_files_functions_classes_integration():
    db = await get_graph_db()
    if not await db.health_check():
        pytest.skip("neo4j offline")
    async with await db.get_session() as session:
        tx = await session.begin_transaction()
        await tx.run("MERGE (:File {path:'/x.py'})")
        await tx.run("MERGE (:File {path:'/x.py'})")
        await tx.run("MERGE (:Function {name:'f', file_path:'/x.py'})")
        await tx.run("MERGE (:Function {name:'f', file_path:'/x.py'})")
        await tx.run("MERGE (:Class {name:'C', file_path:'/x.py'})")
        await tx.run("MERGE (:Class {name:'C', file_path:'/x.py'})")
        await tx.run("MATCH (f:Function {name:'f', file_path:'/x.py'}), (g:Function {name:'f', file_path:'/x.py'}) MERGE (f)-[:CALLS]->(g)")
        await tx.run("MATCH (c:Class {name:'C', file_path:'/x.py'}), (p:Class {name:'C', file_path:'/x.py'}) MERGE (c)-[:IMPLEMENTS]->(p)")
        await tx.commit()
    repo = KnowledgeRepository(db)
    t0 = time.time()
    res_fc = await repo.dedupe_functions_and_classes()
    elapsed_fc = time.time() - t0
    assert elapsed_fc < 0.5
    if elapsed_fc > 0.3:
        pytest.warns(UserWarning)
    t1 = time.time()
    res_f = await repo.dedupe_files()
    elapsed_f = time.time() - t1
    assert elapsed_f < 0.5
    files = await db.query("MATCH (f:File) RETURN count(f) as cnt")
    assert files[0]["cnt"] == 1
    funcs = await db.query("MATCH (f:Function {name:'f', file_path:'/x.py'}) RETURN count(f) as cnt")
    assert funcs[0]["cnt"] == 1
    classes = await db.query("MATCH (c:Class {name:'C', file_path:'/x.py'}) RETURN count(c) as cnt")
    assert classes[0]["cnt"] == 1