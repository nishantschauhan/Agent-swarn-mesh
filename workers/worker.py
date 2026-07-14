"""Execution worker: consumes task_queue, runs a tool-using LLM agent with Qdrant-backed
shared memory, and streams live reasoning to Redis Pub/Sub `agent_logs`."""
import concurrent.futures
import logging
import os

import pika
import redis
from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from memory import get_job_context, store_task_result
from shared.schemas import AgentLogEvent, TaskPayload, TaskStatus
from tools import AVAILABLE_TOOLS, TOOLS_BY_NAME

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [worker] %(levelname)s %(message)s")
logger = logging.getLogger("worker")

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
TASK_QUEUE = "task_queue"
AGENT_LOGS_CHANNEL = "agent_logs"
LLM_TIMEOUT_SECONDS = 60
MAX_AGENT_STEPS = 4

redis_client = redis.from_url(REDIS_URL, decode_responses=True)
_executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)


def publish_log(event: AgentLogEvent) -> None:
    redis_client.publish(AGENT_LOGS_CHANNEL, event.model_dump_json())


def _invoke_with_timeout(llm, messages) -> AIMessage:
    """Run the (blocking) LLM call on a worker thread and enforce a hard wall-clock timeout."""
    future = _executor.submit(llm.invoke, messages)
    return future.result(timeout=LLM_TIMEOUT_SECONDS)


def run_agent(task: TaskPayload, context: str) -> str:
    """Bounded tool-calling loop; streams each reasoning/tool step to Redis as it happens."""
    llm = ChatGoogleGenerativeAI(
        model=GEMINI_MODEL, temperature=0, api_key=GEMINI_API_KEY
    ).bind_tools(AVAILABLE_TOOLS)

    step_name = task.payload.get("step", "unknown")
    goal = task.payload.get("prompt", "")
    detail = task.payload.get("detail", "")

    system_prompt = (
        "You are an execution agent completing one step of a larger job. "
        "Use the web_fetch and calculator tools when they would genuinely help. "
        "When you have enough information, respond with a concise final answer and no further tool calls."
    )
    user_prompt = f"Overall goal: {goal}\nCurrent step: {step_name}\n{detail}\n"
    if context:
        user_prompt += f"\nContext from prior steps in this job:\n{context}\n"

    messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]

    for i in range(MAX_AGENT_STEPS):
        response = _invoke_with_timeout(llm, messages)
        messages.append(response)

        if response.content:
            publish_log(
                AgentLogEvent(
                    job_id=task.job_id,
                    task_id=task.task_id,
                    status=TaskStatus.PROCESSING,
                    message=f"Task {task.task_id} reasoning (step {i + 1})",
                    agent_thought=response.content,
                )
            )

        if not response.tool_calls:
            return response.content or "(agent returned no content)"

        for call in response.tool_calls:
            tool_fn = TOOLS_BY_NAME.get(call["name"])
            result = tool_fn.invoke(call["args"]) if tool_fn else f"Unknown tool: {call['name']}"
            publish_log(
                AgentLogEvent(
                    job_id=task.job_id,
                    task_id=task.task_id,
                    status=TaskStatus.PROCESSING,
                    message=f"Task {task.task_id} used tool '{call['name']}'",
                    agent_thought=f"{call['name']}({call['args']}) -> {str(result)[:300]}",
                )
            )
            messages.append(ToolMessage(content=str(result), tool_call_id=call["id"]))

    return "(max reasoning steps reached without a final answer)"


def handle_task(channel, method, properties, body: bytes) -> None:
    task = TaskPayload.model_validate_json(body)
    logger.info("Picked up task %s (job %s)", task.task_id, task.job_id)

    publish_log(
        AgentLogEvent(
            job_id=task.job_id,
            task_id=task.task_id,
            status=TaskStatus.PROCESSING,
            message=f"Task {task.task_id} processing...",
            agent_thought=f"Working on step: {task.payload.get('step', 'unknown')}",
        )
    )

    try:
        context = get_job_context(task.job_id)
        output = run_agent(task, context)
        store_task_result(task.job_id, task.task_id, task.payload.get("step", ""), output)

        publish_log(
            AgentLogEvent(
                job_id=task.job_id,
                task_id=task.task_id,
                status=TaskStatus.COMPLETED,
                message=f"Task {task.task_id} complete.",
                agent_thought=output,
            )
        )
        logger.info("Completed task %s (job %s)", task.task_id, task.job_id)

    except Exception as exc:
        logger.error("Task %s (job %s) failed: %s", task.task_id, task.job_id, exc)
        publish_log(
            AgentLogEvent(
                job_id=task.job_id,
                task_id=task.task_id,
                status=TaskStatus.FAILED,
                message=f"Task {task.task_id} failed: {exc}",
                agent_thought=f"Error: {exc}",
            )
        )
    finally:
        # Always ack, even on failure: a poison-pill task must not be redelivered forever.
        channel.basic_ack(delivery_tag=method.delivery_tag)


def main() -> None:
    connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
    channel = connection.channel()
    channel.queue_declare(queue=TASK_QUEUE, durable=True)
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=TASK_QUEUE, on_message_callback=handle_task)

    logger.info("Worker started, waiting for tasks on '%s'", TASK_QUEUE)
    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        channel.stop_consuming()
        connection.close()


if __name__ == "__main__":
    main()
