import asyncio
import os
import sys

# Adiciona o diretório /app ao path para importar o Janus
sys.path.append("/app")

from app.core.agents.meta_agent import get_meta_agent
from app.config import settings


async def test_cycle():
    print("Starting Meta Agent internal cycle test...")
    agent = get_meta_agent()

    try:
        print("Invoking run_analysis_cycle()...")
        report = await agent.run_analysis_cycle()
        print("\nSUCCESS!")
        print(f"Cycle ID: {report.cycle_id}")
        print(f"Status: {report.overall_status}")
        print(f"Diagnosis: {report.summary}")
        print(f"Issues: {len(report.issues_detected)}")
        print(f"Recommendations: {len(report.recommendations)}")
    except Exception as e:
        print(f"\nFATAL ERROR during cycle: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_cycle())
