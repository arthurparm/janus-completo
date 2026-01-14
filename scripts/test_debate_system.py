import asyncio
import logging
import sys
import os

# Add 'janus' directory to sys.path to allow imports like 'app.core...'
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "..", "janus"))
sys.path.append(project_root)

from app.core.agents.debate_orchestrator import debate_graph

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

async def main():
    print(">>> Starting Debate System Test (LangGraph Mode)...")
    
    initial_state = {
        "task_id": "test-debate-001",
        "goal": "Create a Python function to calculate the Fibonacci sequence recursively with memoization. Must handle negative inputs raising ValueError.",
        "iteration": 0,
        "max_iterations": 3,
        "history": [],
        "code": None,
        "critique": None,
        "status": "in_progress"
    }
    
    print(f"Goal: {initial_state['goal']}")
    
    try:
        # Run the graph
        # Note: 'astream' yields dictionaries where keys are node names and values are state updates
        async for output in debate_graph.astream(initial_state):
            for node_name, state_update in output.items():
                print(f"\n--- Node Finished: {node_name} ---")
                if "code" in state_update:
                    print(f"[Proponent] Code generated (Length: {len(state_update['code'])})")
                    print(f"Preview: {state_update['code'][:100]}...")
                if "critique" in state_update:
                    critique = state_update['critique']
                    approved = critique.get('approved')
                    print(f"[Critic] Approved: {approved}")
                    if not approved:
                        print(f"Issues: {len(critique.get('issues', []))}")
                        for issue in critique.get('issues', []):
                            print(f" - {issue.get('severity')}: {issue.get('description')}")
        
        print("\n>>> Test Completed.")
        
    except Exception as e:
        print(f"Test Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
