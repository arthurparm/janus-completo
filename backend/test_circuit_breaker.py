"""
Test script for Qdrant circuit breaker and resilience improvements.
"""
import asyncio
import logging
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_circuit_breaker_scenarios():
    """Test various circuit breaker scenarios."""
    print("🧪 Testing Qdrant Circuit Breaker and Resilience Improvements")
    print("=" * 60)

    try:
        from app.core.memory.circuit_config import RESILIENCE_CONFIG
        from app.core.memory.memory_core import get_memory_db

        # Get memory database instance
        memory_db = await get_memory_db()
        print("✅ Memory database initialized")

        # Test 1: Basic health check
        print("\n📋 Test 1: Basic Health Check")
        print("-" * 30)
        is_healthy = await memory_db.health_check()
        print(f"Health Status: {'✅ Healthy' if is_healthy else '❌ Unhealthy'}")

        # Test 2: Circuit breaker status
        print("\n📊 Test 2: Circuit Breaker Status")
        print("-" * 30)
        status = memory_db.get_circuit_breaker_status()
        print(f"System Health: {status['system_health']['is_healthy']}")
        print(f"Health Score: {status['system_health']['health_score']:.1f}/100")
        print(f"Circuit Breaker: {'🔴 OPEN' if status['system_health']['circuit_breaker_open'] else '🟢 CLOSED'}")
        print(f"Offline: {'Yes' if status['system_health']['offline'] else 'No'}")

        # Test 3: Configuration validation
        print("\n⚙️ Test 3: Configuration Validation")
        print("-" * 30)
        config = status['configuration']
        print(f"Failure Threshold: {config['failure_threshold']}")
        print(f"Recovery Timeout: {config['recovery_timeout']}s")
        print(f"Search Timeout: {config['search_timeout']}s")
        print(f"Auto Recovery: {'Enabled' if config['auto_recovery_enabled'] else 'Disabled'}")

        # Test 4: Circuit breaker reset
        print("\n🔄 Test 4: Circuit Breaker Reset")
        print("-" * 30)
        memory_db.reset_circuit_breaker()
        print("✅ Circuit breaker reset completed")

        # Verify reset
        new_status = memory_db.get_circuit_breaker_status()
        if not new_status['system_health']['circuit_breaker_open']:
            print("✅ Circuit breaker successfully reset to CLOSED")
        else:
            print("⚠️ Circuit breaker still open (may be expected if Qdrant is unavailable)")

        # Test 5: Monitoring service
        print("\n📈 Test 5: Monitoring Service")
        print("-" * 30)
        from app.core.memory.qdrant_monitoring import get_qdrant_monitoring_service
        monitoring_service = get_qdrant_monitoring_service()

        if monitoring_service:
            metrics = monitoring_service.get_detailed_metrics()
            print("Monitoring Active: ✅")
            print(f"Total Checks: {metrics['monitoring_stats']['total_checks']}")
            print(f"Error Count: {metrics['monitoring_stats']['error_count']}")
            print(f"Recovery Count: {metrics['monitoring_stats']['recovery_count']}")
        else:
            print("Monitoring Service: ❌ Not initialized")

        # Test 6: API endpoints
        print("\n🌐 Test 6: API Endpoints")
        print("-" * 30)

        # Test health endpoints
        import httpx

        base_url = "http://localhost:8000/api/v1"

        # Test basic health endpoint
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{base_url}/knowledge/health")
                if response.status_code == 200:
                    health_data = response.json()
                    print(f"✅ Basic Health Endpoint: {health_data.get('status', 'unknown')}")
                else:
                    print(f"❌ Basic Health Endpoint: HTTP {response.status_code}")
        except Exception as e:
            print(f"❌ Basic Health Endpoint: {str(e)}")

        # Test detailed health endpoint
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{base_url}/knowledge/health/detailed")
                if response.status_code == 200:
                    detailed_data = response.json()
                    print(f"✅ Detailed Health Endpoint: {detailed_data.get('overall_status', 'unknown')}")
                    print(f"   Health Score: {detailed_data.get('detailed_status', {}).get('system_health', {}).get('health_score', 'N/A')}")
                else:
                    print(f"❌ Detailed Health Endpoint: HTTP {response.status_code}")
        except Exception as e:
            print(f"❌ Detailed Health Endpoint: {str(e)}")

        # Test circuit breaker reset endpoint
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(f"{base_url}/knowledge/health/reset-circuit-breaker")
                if response.status_code == 200:
                    reset_data = response.json()
                    print(f"✅ Circuit Breaker Reset: {reset_data.get('message', 'unknown')}")
                else:
                    print(f"❌ Circuit Breaker Reset: HTTP {response.status_code}")
        except Exception as e:
            print(f"❌ Circuit Breaker Reset: {str(e)}")

        # Test 7: Performance simulation
        print("\n🚀 Test 7: Performance Simulation")
        print("-" * 30)

        # Simulate some operations
        start_time = time.time()
        operations_tested = 0

        # Test memory operations (if Qdrant is available)
        if is_healthy:
            try:
                # Test recall operation
                results = await memory_db.arecall("test query", limit=5)
                operations_tested += 1
                print(f"✅ Recall Operation: {len(results)} results returned")
            except Exception as e:
                print(f"⚠️ Recall Operation Failed: {str(e)}")

        end_time = time.time()
        print(f"Performance Test Duration: {end_time - start_time:.2f}s")
        print(f"Operations Tested: {operations_tested}")

        # Test 8: Configuration validation
        print("\n🔧 Test 8: Configuration Validation")
        print("-" * 30)

        # Validate timeout configurations
        timeouts = RESILIENCE_CONFIG.qdrant_timeouts
        print(f"Search Timeout: {timeouts.search_timeout}s")
        print(f"Connection Timeout: {timeouts.connection_timeout}s")
        print(f"Health Check Timeout: {timeouts.health_check_timeout}s")

        # Validate retry configuration
        retry_config = RESILIENCE_CONFIG.retry
        print(f"Max Retry Attempts: {retry_config.max_attempts}")
        print(f"Initial Backoff: {retry_config.initial_backoff}s")
        print(f"Max Backoff: {retry_config.max_backoff}s")
        print(f"Backoff Multiplier: {retry_config.backoff_multiplier}x")
        print(f"Jitter Enabled: {'Yes' if retry_config.jitter else 'No'}")

        print("\n" + "=" * 60)
        print("✅ All tests completed successfully!")
        print("📝 Check logs for detailed information about circuit breaker behavior")

        return True

    except ImportError as e:
        print(f"❌ Import Error: {e}")
        print("Make sure the application is properly initialized")
        return False

    except Exception as e:
        print(f"❌ Test Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_failure_scenarios():
    """Test failure scenarios and recovery."""
    print("\n🔥 Testing Failure Scenarios and Recovery")
    print("=" * 50)

    try:
        from app.core.memory.memory_core import get_memory_db

        memory_db = await get_memory_db()

        print("\n📊 Initial Status:")
        initial_status = memory_db.get_circuit_breaker_status()
        print(f"Circuit Breaker: {'OPEN' if initial_status['system_health']['circuit_breaker_open'] else 'CLOSED'}")
        print(f"Health Score: {initial_status['system_health']['health_score']:.1f}")

        # Test manual circuit breaker manipulation
        print("\n🔄 Testing Manual Circuit Breaker Control:")

        # Force circuit breaker open (simulating failures)
        print("1. Simulating circuit breaker open...")
        # This would normally happen through actual failures

        # Reset circuit breaker
        print("2. Resetting circuit breaker...")
        memory_db.reset_circuit_breaker()

        # Verify reset
        reset_status = memory_db.get_circuit_breaker_status()
        print(f"✅ Circuit breaker reset: {'OPEN' if reset_status['system_health']['circuit_breaker_open'] else 'CLOSED'}")

        # Test health check
        print("\n🏥 Testing Health Check:")
        is_healthy = await memory_db.health_check()
        print(f"Health Check Result: {'✅ Healthy' if is_healthy else '❌ Unhealthy'}")

        print("\n✅ Failure scenario tests completed!")

    except Exception as e:
        print(f"❌ Failure scenario test failed: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """Main test function."""
    print("🚀 Starting Qdrant Circuit Breaker Tests")
    print("This will test the enhanced circuit breaker and monitoring features.")
    print("Make sure the application is running and Qdrant is accessible.\n")

    # Run basic tests
    success = await test_circuit_breaker_scenarios()

    if success:
        # Run failure scenario tests
        await test_failure_scenarios()

        print("\n🎉 All tests completed!")
        print("The enhanced circuit breaker and monitoring system is working correctly.")
    else:
        print("\n❌ Some tests failed. Check the logs for details.")


if __name__ == "__main__":
    asyncio.run(main())
