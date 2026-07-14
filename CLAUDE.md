# agent-swarm-mesh

Event-driven multi-agent swarm: FastAPI planner pushes tasks onto a RabbitMQ
queue, workers consume and execute them, and a Socket.io gateway relays
live agent logs from a Redis Pub/Sub channel to connected clients.

## Architecture

- **rabbitmq** — durable `task_queue` for planner → worker handoff.
- **redis** — Pub/Sub channel `agent_logs` for live log broadcast; also usable
  for shared ephemeral state.
- **gateway** (port 8000) — FastAPI + python-socketio; subscribes to
  `agent_logs` and re-broadcasts over WebSockets.
- **planner** (port 8001) — FastAPI; `POST /api/v1/execute` breaks a user
  goal into 3 mock tasks and publishes them to `task_queue`.
- **workers** — pika consumer(s); pull from `task_queue`, sleep 3s to mock
  LLM latency, publish progress + completion events to `agent_logs`.

## Running

```bash
docker compose up -d --build      # start everything
docker compose logs -f            # tail all service logs
docker compose down                # stop and remove containers
docker compose down -v             # stop and wipe volumes (RabbitMQ/Redis data)
```

Ports:
- RabbitMQ AMQP: `localhost:5672`
- RabbitMQ management UI: `localhost:15672` (guest/guest)
- Redis: `localhost:6379`
- Gateway (WebSocket/Socket.io): `localhost:8000`
- Planner API: `localhost:8001`

## Verifying the plumbing

1. Bring the stack up: `docker compose up -d --build`
2. Trigger a job:
   ```bash
   curl -X POST http://localhost:8001/api/v1/execute \
     -H "Content-Type: application/json" \
     -d '{"prompt": "Research competitor pricing"}'
   ```
3. Watch live logs stream from the gateway via a Socket.io/WebSocket client
   connected to `ws://localhost:8000`, subscribed to the `agent_logs` event.
4. Cross-check with `docker compose logs -f workers` to confirm each task
   was picked up, processed (3s mock delay), and marked complete.

## Constraints / conventions

- No real LLM calls yet — workers use `time.sleep(3)` to mock processing.
  Do not wire in OpenAI/Anthropic/Gemini SDKs until the distributed plumbing
  (queue → worker → pubsub → gateway) is proven end-to-end.
- All services share the `swarm-net` Docker network and resolve each other
  by service name (`rabbitmq`, `redis`).
- Event payloads must conform to `shared/schemas.py` (`TaskPayload`,
  `AgentLogEvent`) — keep producers/consumers in sync with that file.
