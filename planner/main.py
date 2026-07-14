"""Planner service: uses an LLM to break a user goal into discrete tasks and pushes them to RabbitMQ."""
import concurrent.futures
import logging
import os
import uuid

import pika
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel

from shared.schemas import TaskPayload, TaskPlan, TaskStatus, TaskStep

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [planner] %(levelname)s %(message)s")
logger = logging.getLogger("planner")

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
TASK_QUEUE = "task_queue"
LLM_TIMEOUT_SECONDS = 45
CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:3000").split(",")
    if origin.strip()
]

FALLBACK_STEPS = [
    TaskStep(step="Research and gather context"),
    TaskStep(step="Draft a plan of action"),
    TaskStep(step="Summarize and finalize output"),
]

app = FastAPI(title="Planner Service")
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)
_executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)


class ExecuteRequest(BaseModel):
    prompt: str


def generate_plan(prompt: str) -> list[TaskStep]:
    """Ask the LLM to break `prompt` into discrete steps; fall back to mock steps on any failure."""
    try:
        llm = ChatGoogleGenerativeAI(model=GEMINI_MODEL, temperature=0, api_key=GEMINI_API_KEY)
        structured_llm = llm.with_structured_output(TaskPlan)
        future = _executor.submit(
            structured_llm.invoke,
            [
                SystemMessage(
                    content=(
                        "You are a planning agent. Break the user's goal into 2-6 discrete, "
                        "sequential, actionable steps. Keep each step short."
                    )
                ),
                HumanMessage(content=prompt),
            ],
        )
        plan: TaskPlan = future.result(timeout=LLM_TIMEOUT_SECONDS)
        if not plan.steps:
            raise ValueError("LLM returned an empty plan")
        logger.info("LLM generated %d dynamic steps for prompt: %s", len(plan.steps), prompt)
        return plan.steps
    except Exception as exc:
        logger.warning("Dynamic planning failed (%s); falling back to mock steps", exc)
        return FALLBACK_STEPS


def publish_tasks(job_id: str, prompt: str, steps: list[TaskStep]) -> list[dict]:
    """Publish one TaskPayload per step to task_queue; return summaries for the caller/UI."""
    connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
    channel = connection.channel()
    channel.queue_declare(queue=TASK_QUEUE, durable=True)

    tasks = []
    for step in steps:
        task_id = str(uuid.uuid4())
        task = TaskPayload(
            job_id=job_id,
            task_id=task_id,
            status=TaskStatus.PENDING,
            payload={"prompt": prompt, "step": step.step, "detail": step.detail},
        )
        channel.basic_publish(
            exchange="",
            routing_key=TASK_QUEUE,
            body=task.model_dump_json(),
            properties=pika.BasicProperties(delivery_mode=2),  # persistent
        )
        logger.info("Published task %s (%s) for job %s", task_id, step.step, job_id)
        tasks.append({"task_id": task_id, "step": step.step, "detail": step.detail})

    connection.close()
    return tasks


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/api/v1/execute", status_code=202)
async def execute(request: ExecuteRequest):
    job_id = str(uuid.uuid4())
    logger.info("Received goal for job %s: %s", job_id, request.prompt)

    steps = generate_plan(request.prompt)
    tasks = publish_tasks(job_id, request.prompt, steps)

    logger.info("Job %s queued with %d tasks", job_id, len(tasks))
    return JSONResponse(
        status_code=202,
        content={
            "job_id": job_id,
            "task_ids": [t["task_id"] for t in tasks],
            "tasks": tasks,
            "status": "accepted",
        },
    )
