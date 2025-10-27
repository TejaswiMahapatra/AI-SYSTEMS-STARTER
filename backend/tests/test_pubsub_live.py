#!/usr/bin/env python
"""
Live test for Redis Pub/Sub implementation.

This script tests that:
1. Worker can publish progress updates
2. WebSocket can subscribe and receive updates
3. No hanging issues

Usage:
    python backend/tests/test_pubsub_live.py
"""

import asyncio
from backend.core.redis_client import get_redis_pubsub


async def test_concurrent():
    """Test publisher and subscriber running concurrently."""
    print("=" * 80)
    print("Redis Pub/Sub Live Test")
    print("=" * 80)

    test_channel = "test:concurrent"

    async def publisher():
        """Publish messages every second."""
        pubsub = get_redis_pubsub()
        for i in range(5):
            await asyncio.sleep(1)
            message = {"id": i, "message": f"Message {i}"}
            num_subs = await pubsub.publish(test_channel, message)
            print(f"[Publisher] Sent message {i} ({num_subs} subscribers)")

    async def subscriber():
        """Subscribe and receive messages."""
        pubsub = get_redis_pubsub()
        print("[Subscriber] Waiting for messages...\n")

        count = 0
        async for msg in pubsub.subscribe(test_channel):
            count += 1
            print(f"[Subscriber] Received: {msg}")

            if count >= 5:
                print("\n[Subscriber] Got all messages, stopping")
                break


    await asyncio.gather(
        subscriber(),
        publisher()
    )

    print("\n✓ Test completed - No hanging!\n")


async def test_document_progress():
    """Test with document progress channel (simulates real usage)."""
    print("=" * 80)
    print("Document Progress Simulation")
    print("=" * 80)

    document_id = "test-doc-12345"
    channel = f"document:{document_id}:progress"

    async def simulate_worker():
        """Simulate worker publishing progress."""
        pubsub = get_redis_pubsub()

        progress_updates = [
            {"status": "processing", "message": "Starting...", "progress": 0},
            {"status": "processing", "message": "Downloading PDF...", "progress": 15},
            {"status": "processing", "message": "Extracting text...", "progress": 30},
            {"status": "processing", "message": "Chunking text...", "progress": 50},
            {"status": "processing", "message": "Generating embeddings...", "progress": 70},
            {"status": "processing", "message": "Storing vectors...", "progress": 90},
            {"status": "completed", "message": "Done!", "progress": 100},
        ]

        for update in progress_updates:
            await asyncio.sleep(0.5)
            update["document_id"] = document_id
            num_subs = await pubsub.publish(channel, update)
            print(f"[Worker] {update['message']} ({update['progress']}%) [{num_subs} subscribers]")

    async def simulate_websocket():
        """Simulate WebSocket client."""
        pubsub = get_redis_pubsub()
        print(f"[WebSocket] Listening for progress on {document_id}...\n")

        async for update in pubsub.subscribe(channel):
            print(f"[WebSocket] ← {update['message']} ({update['progress']}%)")

            if update.get('status') == 'completed':
                print("\n[WebSocket] Processing complete!")
                break

    await asyncio.gather(
        simulate_websocket(),
        simulate_worker()
    )

    print("\n✓ Document progress test completed\n")


async def main():
    """Run all tests."""
    print("\n")

    try:
        await test_concurrent()
        await test_document_progress()

        print("=" * 80)
        print("ALL TESTS PASSED")
        print("=" * 80)
        print("\nRedis pub/sub is working correctly!")
        print("No hanging issues detected.")
        print("Ready for production use.\n")

    except Exception as e:
        print(f"\nTEST FAILED: {e}\n")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
