"""
Redis client for caching and job queue management.

Copyright 2025 Tejaswi Mahapatra
Licensed under the Apache License, Version 2.0
"""

import json
from typing import Any, Optional
from redis.asyncio import Redis, ConnectionPool
from redis.exceptions import RedisError
from backend.config import settings


_redis_pool: Optional[ConnectionPool] = None
_redis_client: Optional[Redis] = None


def get_redis_pool() -> ConnectionPool:
    """Get or create Redis connection pool."""
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = ConnectionPool.from_url(
            settings.redis_url,
            decode_responses=True,
            max_connections=10,
        )
    return _redis_pool


def get_redis() -> Redis:
    """
    Get Redis client instance.

    Usage:
        redis = get_redis()
        await redis.set("key", "value")
        value = await redis.get("key")
    """
    global _redis_client
    if _redis_client is None:
        pool = get_redis_pool()
        _redis_client = Redis(connection_pool=pool)
    return _redis_client


async def close_redis() -> None:
    """Close Redis connections gracefully."""
    global _redis_client, _redis_pool

    if _redis_client:
        await _redis_client.aclose()
        _redis_client = None

    if _redis_pool:
        await _redis_pool.aclose()
        _redis_pool = None


class RedisCache:
    """Helper class for common Redis caching patterns."""

    def __init__(self):
        self.redis = get_redis()

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache. Returns None if not found."""
        try:
            value = await self.redis.get(key)
            if value:
                return json.loads(value)
            return None
        except RedisError:
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache (will be JSON serialized)
            ttl: Time to live in seconds (optional)

        Returns:
            True if successful, False otherwise
        """
        try:
            serialized = json.dumps(value)
            if ttl:
                await self.redis.setex(key, ttl, serialized)
            else:
                await self.redis.set(key, serialized)
            return True
        except (RedisError, TypeError):
            return False

    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        try:
            await self.redis.delete(key)
            return True
        except RedisError:
            return False

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        try:
            return await self.redis.exists(key) > 0
        except RedisError:
            return False


class RedisQueue:
    """Helper class for Redis-based job queue."""

    def __init__(self, queue_name: str = "default"):
        self.redis = get_redis()
        self.queue_name = f"queue:{queue_name}"

    async def enqueue(self, job_data: dict) -> bool:
        """
        Add job to queue.

        Args:
            job_data: Job data as dictionary

        Returns:
            True if successful, False otherwise
        """
        try:
            serialized = json.dumps(job_data)
            await self.redis.rpush(self.queue_name, serialized)
            return True
        except (RedisError, TypeError):
            return False

    async def dequeue(self, timeout: int = 0) -> Optional[dict]:
        """
        Get job from queue (blocking).

        Args:
            timeout: Block timeout in seconds (0 = block forever)

        Returns:
            Job data as dictionary, or None if timeout
        """
        try:
            result = await self.redis.blpop(self.queue_name, timeout=timeout)
            if result:
                _, job_data = result
                return json.loads(job_data)
            return None
        except (RedisError, json.JSONDecodeError):
            return None

    async def size(self) -> int:
        """Get queue size."""
        try:
            return await self.redis.llen(self.queue_name)
        except RedisError:
            return 0

    async def clear(self) -> bool:
        """Clear all jobs from queue."""
        try:
            await self.redis.delete(self.queue_name)
            return True
        except RedisError:
            return False


# Factory functions for dependency injection
def get_redis_queue(queue_name: str = "ingestion_queue") -> RedisQueue:
    """
    Get a RedisQueue instance for dependency injection.

    Args:
        queue_name: Name of the Redis queue (default: "ingestion_queue")

    Returns:
        RedisQueue instance
    """
    return RedisQueue(queue_name=queue_name)


def get_redis_client() -> Redis:
    """
    Get a Redis client instance.
    Alias for get_redis() for consistency.
    """
    return get_redis()


class RedisPubSub:
    """
    Helper class for Redis Pub/Sub (real-time progress updates).

    IMPORTANT: Pub/Sub requires a SEPARATE Redis connection per subscriber
    to avoid blocking the main connection pool.

    Usage (Publisher):
        pubsub = RedisPubSub()
        await pubsub.publish("channel:name", {"status": "processing"})

    Usage (Subscriber):
        pubsub = RedisPubSub()
        async for message in pubsub.subscribe("channel:name"):
            print(message)
            if message.get("status") == "completed":
                break
    """

    def __init__(self):
        """Initialize pub/sub with main Redis client for publishing."""
        self.redis = get_redis()

    async def publish(self, channel: str, message: dict) -> int:
        """
        Publish a message to a channel.

        Args:
            channel: Channel name (e.g., "document:abc123:progress")
            message: Message dict (will be JSON serialized)

        Returns:
            Number of subscribers that received the message (0 if none)

        Example:
            await pubsub.publish(
                "document:123:progress",
                {"status": "processing", "progress": 50}
            )
        """
        try:
            serialized = json.dumps(message)
            num_subscribers = await self.redis.publish(channel, serialized)
            return num_subscribers
        except (RedisError, TypeError) as e:
            print(f"Error publishing to {channel}: {e}")
            return 0

    async def subscribe(self, channel: str):
        """
        Subscribe to a channel and yield messages.

        IMPORTANT: Creates a NEW Redis connection for this subscription
        to avoid blocking other operations.

        Args:
            channel: Channel name to subscribe to

        Yields:
            Decoded message dictionaries from the channel

        Example:
            async for msg in pubsub.subscribe("document:123:progress"):
                print(f"Progress: {msg['progress']}%")
                if msg.get("status") == "completed":
                    break

        Note: Connection is automatically cleaned up when generator exits
        """
        pubsub_redis = Redis(
            connection_pool=ConnectionPool.from_url(
                settings.redis_url,
                decode_responses=True,
                max_connections=2  # Small pool for pub/sub
            )
        )

        pubsub = pubsub_redis.pubsub()

        try:
            await pubsub.subscribe(channel)
            print(f"[PubSub] Subscribed to channel: {channel}")

            async for raw_message in pubsub.listen():
                if raw_message["type"] == "message":
                    try:
                        data = json.loads(raw_message["data"])
                        yield data
                    except json.JSONDecodeError as e:
                        print(f"[PubSub] Failed to decode message: {e}")
                        continue

        except Exception as e:
            print(f"[PubSub] Error in subscription: {e}")
            raise

        finally:
            try:
                await pubsub.unsubscribe(channel)
                await pubsub.close()
                await pubsub_redis.aclose()
                print(f"[PubSub] Unsubscribed from channel: {channel}")
            except Exception as e:
                print(f"[PubSub] Error during cleanup: {e}")


def get_redis_pubsub() -> RedisPubSub:
    """
    Get a RedisPubSub instance.

    Returns:
        RedisPubSub instance for publishing and subscribing to channels
    """
    return RedisPubSub()


async def check_redis_health() -> bool:
    """
    Check if Redis connection is healthy.
    Returns True if connection is successful, False otherwise.
    """
    try:
        redis = get_redis()
        await redis.ping()
        return True
    except Exception:
        return False
