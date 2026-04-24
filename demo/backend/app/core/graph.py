"""Neo4j / Graphiti driver.

Graphiti adds bi-temporal knowledge-graph features on top of Neo4j:
episodes, entities, facts with valid_at / invalid_at intervals. We only
use it for pits 5/6/8 where temporal or versioned facts are the point.
"""
from __future__ import annotations

from neo4j import AsyncDriver, AsyncGraphDatabase

from app.config import get_settings

_driver: AsyncDriver | None = None


def get_driver() -> AsyncDriver:
    global _driver
    if _driver is None:
        s = get_settings()
        _driver = AsyncGraphDatabase.driver(
            s.neo4j_uri, auth=(s.neo4j_user, s.neo4j_password)
        )
    return _driver


async def run_cypher(query: str, parameters: dict | None = None) -> list[dict]:
    driver = get_driver()
    async with driver.session() as session:
        result = await session.run(query, parameters or {})
        return [record.data() async for record in result]


async def close() -> None:
    global _driver
    if _driver is not None:
        await _driver.close()
        _driver = None
