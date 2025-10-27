"""
WebSocket API for Real-Time Progress Updates

This module provides WebSocket endpoints for tracking document processing progress.
Clients connect to /ws/{document_id} and receive real-time updates as the
ingestion worker processes their document.

Progress updates include:
- Current status (queued, processing, completed, failed)
- Progress percentage (0-100)
- Human-readable messages
- Timestamp
"""

import asyncio
import json
from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from redis import asyncio as aioredis
from backend.core.redis_client import get_redis_client, get_redis_pubsub
from backend.config import get_settings

settings = get_settings()
router = APIRouter(tags=["websocket"])



# WebSocket Connection Manager

class ConnectionManager:
    """
    Manage WebSocket connections for document progress tracking.

    This manager:
    1. Accepts WebSocket connections
    2. Subscribes to Redis pub/sub for that document
    3. Forwards progress updates to the WebSocket client
    4. Handles disconnections gracefully
    """

    def __init__(self):
        """Initialize connection manager."""
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, document_id: str, websocket: WebSocket):
        """
        Accept a WebSocket connection and subscribe to progress updates.

        Args:
            document_id: Document UUID to track
            websocket: WebSocket connection
        """
        await websocket.accept()
        self.active_connections[document_id] = websocket
        print(f"WebSocket connected: {document_id[:8]}...")

    def disconnect(self, document_id: str):
        """
        Remove a WebSocket connection.

        Args:
            document_id: Document UUID
        """
        if document_id in self.active_connections:
            del self.active_connections[document_id]
            print(f"WebSocket disconnected: {document_id[:8]}...")

    async def send_message(self, document_id: str, message: dict):
        """
        Send a message to a connected WebSocket client.

        Args:
            document_id: Document UUID
            message: Message to send (will be JSON-encoded)
        """
        if document_id in self.active_connections:
            websocket = self.active_connections[document_id]
            await websocket.send_json(message)


manager = ConnectionManager()


# WebSocket Endpoint

@router.websocket("/ws/{document_id}")
async def document_progress_websocket(
    websocket: WebSocket,
    document_id: str
):
    """
    WebSocket endpoint for real-time document processing progress.

    Connect to this endpoint to receive live updates as your document
    is processed through the ingestion pipeline.

    Args:
        websocket: WebSocket connection
        document_id: UUID of the document to track

    Message Format:
        {
            "document_id": "123e4567-e89b-12d3-a456-426614174000",
            "status": "processing",
            "message": "Extracting text from PDF...",
            "progress": 30,
            "timestamp": "2024-01-15T10:30:00Z"
        }

    Status Values:
        - "queued": Document is waiting to be processed
        - "processing": Document is being processed
        - "completed": Processing finished successfully
        - "failed": Processing failed (check error_message)

    Example Usage (JavaScript):
        const ws = new WebSocket('ws://localhost:8001/api/v1/ws/123e4567-...');
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            console.log(`${data.message} (${data.progress}%)`);
        };

    Example Usage (Python):
        import websockets
        async with websockets.connect('ws://localhost:8001/api/v1/ws/123e4567-...') as ws:
            while True:
                message = await ws.recv()
                data = json.loads(message)
                print(f"{data['message']} ({data['progress']}%)")
    """

    await manager.connect(document_id, websocket)

    pubsub = get_redis_pubsub()
    channel_name = f"document:{document_id}:progress"

    try:
        await websocket.send_json({
            "type": "connected",
            "document_id": document_id,
            "message": f"Connected to progress updates for document {document_id}"
        })

        async for progress_data in pubsub.subscribe(channel_name):
            await websocket.send_json(progress_data)

            if progress_data.get('status') in ['completed', 'failed']:
                await asyncio.sleep(0.5)  
                break

    except WebSocketDisconnect:
        print(f"Client disconnected: {document_id[:8]}...")

    except Exception as e:
        print(f"WebSocket error for {document_id[:8]}...: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "message": f"WebSocket error: {str(e)}"
            })
        except:
            pass

    finally:
        manager.disconnect(document_id)



# Broadcast Endpoint (for testing)

@router.get("/test/broadcast/{document_id}")
async def test_broadcast(document_id: str, message: str = "Test message"):
    """
    Test endpoint to broadcast a message to WebSocket clients.

    This is useful for testing WebSocket connections without running
    the full ingestion worker.

    Args:
        document_id: Document UUID
        message: Test message to broadcast

    Example:
        GET /api/v1/test/broadcast/123e4567?message=Hello%20World
    """
    redis = get_redis_client()

    test_data = {
        "document_id": document_id,
        "status": "processing",
        "message": message,
        "progress": 50,
        "timestamp": "2024-01-15T10:30:00Z"
    }

    channel_name = f"document:{document_id}:progress"
    await redis.publish(channel_name, json.dumps(test_data))

    return {
        "status": "ok",
        "message": f"Broadcasted to channel: {channel_name}",
        "data": test_data
    }
