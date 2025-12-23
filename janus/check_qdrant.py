import asyncio
from qdrant_client import AsyncQdrantClient
import inspect

async def check_attrs():
    client = AsyncQdrantClient(location=":memory:")
    print("Methods available:")
    for name in dir(client):
        if not name.startswith("_"):
            print(name)
            
    print("\nHas search?", hasattr(client, 'search'))
    print("Has query_points?", hasattr(client, 'query_points'))
    print("Has retrieve?", hasattr(client, 'retrieve'))
    await client.close()

if __name__ == "__main__":
    asyncio.run(check_attrs())
