"""Tools available to the worker's execution agent."""
import ast
import ipaddress
import operator
import socket
from urllib.parse import urlparse

import httpx
from langchain_core.tools import tool

_BLOCKED_HOSTNAMES = {
    "localhost",
    "rabbitmq",
    "redis",
    "qdrant",
    "ollama",
    "gateway",
    "planner",
    "workers",
}

_SAFE_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _is_safe_url(url: str) -> bool:
    """Reject non-http(s) schemes and requests aimed at internal/private infrastructure."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return False
    hostname = parsed.hostname.lower()
    if hostname in _BLOCKED_HOSTNAMES:
        return False
    try:
        resolved = socket.gethostbyname(hostname)
        ip = ipaddress.ip_address(resolved)
    except (socket.gaierror, ValueError):
        return False
    return not (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved)


@tool
def web_fetch(url: str) -> str:
    """Fetch a public URL over HTTP(S) and return up to 2000 characters of its text content."""
    if not _is_safe_url(url):
        return f"Refused to fetch '{url}': blocked scheme/host or unresolvable/internal address."
    try:
        response = httpx.get(url, timeout=10.0, follow_redirects=True)
        response.raise_for_status()
        return response.text[:2000]
    except httpx.HTTPError as exc:
        return f"Failed to fetch '{url}': {exc}"


def _safe_eval(node: ast.AST) -> float:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _SAFE_OPS:
        return _SAFE_OPS[type(node.op)](_safe_eval(node.left), _safe_eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _SAFE_OPS:
        return _SAFE_OPS[type(node.op)](_safe_eval(node.operand))
    raise ValueError(f"Unsupported expression element: {ast.dump(node)}")


@tool
def calculator(expression: str) -> str:
    """Evaluate a basic arithmetic expression (+, -, *, /, %, **), e.g. '12 * (3 + 4)'."""
    try:
        tree = ast.parse(expression, mode="eval")
        return str(_safe_eval(tree.body))
    except Exception as exc:
        return f"Failed to evaluate '{expression}': {exc}"


AVAILABLE_TOOLS = [web_fetch, calculator]
TOOLS_BY_NAME = {t.name: t for t in AVAILABLE_TOOLS}
