# agent-swarm-mesh

Event-Driven Multi-Agent Swarm Architecture

📌 Overview

The Event-Driven Multi-Agent Swarm is an enterprise-grade, asynchronous backend architecture designed to orchestrate long-running, multi-step LLM workflows. Instead of relying on traditional synchronous REST APIs—which are prone to timeouts and bottlenecks during heavy AI inference—this system decouples task planning from execution using a distributed message broker and real-time state management.

🚨 The Engineering Problem

Standard "AI Wrappers" connect a frontend directly to an LLM via HTTP. When an AI agent needs to perform complex, multi-step reasoning, web scraping, or data analysis, the request can take anywhere from 30 seconds to several minutes. This results in dropped connections, frozen UIs, and lost data. Furthermore, multiple independent AI agents struggle to share context without passing massive, token-heavy payloads back and forth.

💡 The Architectural Solution

This project solves the "Agentic Bottleneck" by implementing a fully decoupled microservices mesh:

The Planner API (FastAPI + LLM): Receives the user's high-level goal, dynamically breaks it down into a structured JSON array of discrete sub-tasks, and pushes them to a message queue. It immediately returns a 202 Accepted status, freeing up the client.

The Message Broker (RabbitMQ): Acts as the central nervous system, holding tasks in a resilient queue (task_queue). If a worker node crashes mid-execution, the task is safely preserved and re-routed.

Distributed Workers (Python LLM Agents): Background consumers that pull tasks from RabbitMQ. They are equipped with tool-calling capabilities (Web Fetching, Math, etc.) and handle the heavy lifting of LLM inference (powered by Gemini/Ollama).

Shared Ephemeral Memory (Qdrant Vector DB): Instead of passing massive strings through the queue, workers read and write their findings to a shared Vector Database, allowing Agent B to instantly query what Agent A discovered.

Real-Time Observability (Redis + Socket.io): As workers "think" and execute, they stream their internal reasoning (agent_thought) to a Redis Pub/Sub channel. A dedicated Node.js/FastAPI Gateway listens to this channel and broadcasts the live state to a Next.js frontend via WebSockets.

🛠️ Core Technology Stack

Orchestration: Docker, Docker Compose

Infrastructure: RabbitMQ (Task Routing), Redis (Pub/Sub Event Bus)

State & Memory: Qdrant (Vector Database)

Backend & APIs: Python, FastAPI, WebSockets/Socket.io

AI/MLOps Layer: LangChain, Google Gemini API (or Local Ollama)

Frontend Observability: Next.js, Tailwind CSS

📈 System Impact & Fault Tolerance

By utilizing circuit breakers, dynamic timeouts, and an asynchronous pipeline, this architecture guarantees that LLM degradation or temporary API outages will not crash the core application. It is a blueprint for scalable, production-ready AI infrastructure.

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
