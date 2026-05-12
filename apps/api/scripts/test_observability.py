"""
Script to test observability setup by making API requests and checking traces/logs.
"""

import asyncio
import time

import httpx


async def test_observability():
    """
    Test observability by making requests and checking responses.
    """
    base_url = "http://localhost:4000"

    print("Testing Recipe AI System Observability")
    print("=" * 60)

    async with httpx.AsyncClient() as client:
        # Test 1: Health check
        print("\n1. Testing /health endpoint...")
        try:
            response = await client.get(f"{base_url}/health")
            request_id = response.headers.get("X-Request-ID")

            print(f"   Status: {response.status_code}")
            print(f"   Request ID: {request_id}")
            print(f"   Response: {response.json()}")

            if response.status_code == 200:
                print("   ✓ Health check successful")
            else:
                print("   ✗ Health check failed")
        except Exception as e:
            print(f"   ✗ Error: {e}")

        # Test 2: API v1 status
        print("\n2. Testing /api/v1/status endpoint...")
        try:
            response = await client.get(f"{base_url}/api/v1/status")
            request_id = response.headers.get("X-Request-ID")

            print(f"   Status: {response.status_code}")
            print(f"   Request ID: {request_id}")
            print(f"   Response: {response.json()}")

            if response.status_code == 200:
                print("   ✓ Status check successful")
            else:
                print("   ✗ Status check failed")
        except Exception as e:
            print(f"   ✗ Error: {e}")

        # Test 3: Custom request ID
        print("\n3. Testing custom request ID...")
        try:
            custom_id = "test-observability-12345"
            response = await client.get(
                f"{base_url}/health",
                headers={"X-Request-ID": custom_id}
            )
            returned_id = response.headers.get("X-Request-ID")

            print(f"   Sent ID: {custom_id}")
            print(f"   Returned ID: {returned_id}")

            if returned_id == custom_id:
                print("   ✓ Request ID preserved")
            else:
                print("   ✗ Request ID mismatch")
        except Exception as e:
            print(f"   ✗ Error: {e}")

        # Test 4: Multiple requests for trace generation
        print("\n4. Generating multiple requests for traces...")
        try:
            for i in range(5):
                response = await client.get(f"{base_url}/health")
                print(f"   Request {i+1}/5: Status {response.status_code}")
                await asyncio.sleep(0.1)
            print("   ✓ Multiple requests completed")
        except Exception as e:
            print(f"   ✗ Error: {e}")

    print("\n" + "=" * 60)
    print("Testing completed!")
    print("\nNext steps:")
    print("1. Open Grafana: http://localhost:3001 (admin/admin)")
    print("2. Go to Explore → Tempo")
    print("3. Search for service: recipe-api")
    print("4. View traces from the requests above")
    print("\nFor logs:")
    print("1. Go to Explore → Loki")
    print("2. Query: {service=\"recipe-api\"}")
    print("3. See structured JSON logs with trace IDs")


if __name__ == "__main__":
    asyncio.run(test_observability())