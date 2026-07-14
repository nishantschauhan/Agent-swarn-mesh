"""Gateway service: relays Redis Pub/Sub `agent_logs` messages to WebSocket clients."""
import asyncio
import logging
import os

import redis.asyncio as redis
import socketio
from fastapi import FastAPI

logging.basicConfig(level=logging.INFO, format="%(asctime)s [gateway] %(levelname)s %(message)s")
logger = logging.getLogger("gateway")

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
AGENT_LOGS_CHANNEL = "agent_logs"

sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")
fastapi_app = FastAPI(title="Gateway Service")
app = socketio.ASGIApp(sio, other_asgi_app=fastapi_app)


@fastapi_app.get("/health")
async def health():
    return {"status": "ok"}


@sio.event
async def connect(sid, environ):
    logger.info("Client connected: %s", sid)


@sio.event
async def disconnect(sid):
    logger.info("Client disconnected: %s", sid)


async def redis_listener():
    """Subscribe to `agent_logs` and forward every message to all Socket.io clients."""
    client = redis.from_url(REDIS_URL, decode_responses=True)
    pubsub = client.pubsub()
    await pubsub.subscribe(AGENT_LOGS_CHANNEL)
    logger.info("Subscribed to Redis channel '%s'", AGENT_LOGS_CHANNEL)

    async for message in pubsub.listen():
        if message["type"] != "message":
            continue
        data = message["data"]
        logger.info("Broadcasting agent_logs message: %s", data)
        await sio.emit("agent_logs", data)


@fastapi_app.on_event("startup")
async def startup_event():
    asyncio.create_task(redis_listener())
    logger.info("Gateway startup complete, listening for Redis events")
