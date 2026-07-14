# agent-swarm-mesh

Event-driven multi-agent swarm: a FastAPI planner uses an LLM to break a
user goal into discrete tasks and pushes them onto a RabbitMQ queue,
workers pull tasks and run a tool-using LLM agent with Qdrant-backed
shared memory, and a Socket.io gateway relays live agent logs from a
Redis Pub/Sub channel to a Next.js dashboard.

## Architecture

- **rabbitmq** — durable `task_queue` for planner → worker handoff.
- **redis** — Pub/Sub channel `agent_logs` for live log broadcast.
- **qdrant** — vector store for shared memory between tasks in the same job.
- **gateway** (port 8000) — FastAPI + python-socketio; subscribes to
  `agent_logs` and re-broadcasts over WebSockets.
- **planner** (port 8001) — FastAPI; `POST /api/v1/execute` uses Gemini to
  break a user goal into discrete steps and publishes them to `task_queue`.
- **workers** — pika consumer(s); pull from `task_queue`, run a bounded
  tool-calling Gemini agent (web fetch, calculator), store results in
  Qdrant, and stream progress/completion events to `agent_logs`.
- **ui** (port 3000) — Next.js dashboard that submits jobs to the planner
  and streams live task logs from the gateway.

## Setup

Copy the env template and add your Gemini API key:

```bash
cp .env.example .env
# edit .env and set GEMINI_API_KEY
```

## Running

```bash
docker compose up -d --build      # start everything
docker compose logs -f            # tail all service logs
docker compose down                # stop and remove containers
docker compose down -v             # stop and wipe volumes (RabbitMQ/Redis/Qdrant data)
```

Ports:
- RabbitMQ AMQP: `localhost:5672`
- RabbitMQ management UI: `localhost:15672` (guest/guest)
- Redis: `localhost:6379`
- Qdrant: `localhost:6333`
- Gateway (WebSocket/Socket.io): `localhost:8000`
- Planner API: `localhost:8001`
- UI dashboard: `localhost:3000`

## Testing the plumbing

1. Bring the stack up: `docker compose up -d --build`
2. Trigger a job:
   ```bash
   curl -X POST http://localhost:8001/api/v1/execute \
     -H "Content-Type: application/json" \
     -d '{"prompt": "Research competitor pricing"}'
   ```
3. Open `http://localhost:3000` to watch live task status and agent
   reasoning stream in, or connect a Socket.io/WebSocket client to
   `ws://localhost:8000` subscribed to the `agent_logs` event.
4. Cross-check with `docker compose logs -f workers` to confirm each task
   was picked up, processed, and marked complete.

## Notes

- Event payloads must conform to `shared/schemas.py` (`TaskPayload`,
  `AgentLogEvent`) — keep producers/consumers in sync with that file.
- All services share the `swarm-net` Docker network and resolve each
  other by service name (`rabbitmq`, `redis`, `qdrant`).
- Gemini free-tier API keys are rate- and quota-limited; a `429` in the
  planner/worker logs means the key's quota, not a code bug.
