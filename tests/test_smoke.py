"""Smoke tests for agents-AI.

Validates the repo's structure and module importability without making
external API calls. Heavy ML dependencies (langgraph, langchain providers,
faiss, mcp) are guarded with ``pytest.importorskip`` so the suite runs
even when only a subset is installed.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


def test_repo_layout() -> None:
    assert (ROOT / "main.py").is_file()
    assert (ROOT / "mcp_server.py").is_file()
    assert (ROOT / "requirements.txt").is_file()
    assert (ROOT / "agents").is_dir()
    assert (ROOT / "evals" / "__init__.py").is_file()


def test_readme_present_and_branded() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "agents-AI" in readme
    assert "MCP" in readme


@pytest.mark.parametrize(
    "module",
    [
        "agents/__init__.py",
        "agents/provider.py",
        "agents/basic_agent.py",
        "agents/hitl_agent.py",
        "agents/memory_agent.py",
        "agents/rag_agent.py",
        "agents/tool_agent.py",
        "main.py",
        "mcp_server.py",
    ],
)
def test_module_parses(module: str) -> None:
    """Every Python module in the repo must be syntactically valid.

    This regression guard exists because a previous commit (6d5a8be) shipped
    truncated agent files that could not be imported. AST-parsing each module
    in tests catches that class of breakage at PR review time.
    """
    path = ROOT / module
    if not path.exists():
        pytest.skip(f"{module} does not exist on this branch")
    ast.parse(path.read_text(encoding="utf-8"))


def test_provider_module_imports() -> None:
    pytest.importorskip("langchain_core")
    from agents.provider import get_llm  # noqa: F401  # imported for the side effect of parsing


def test_basic_agent_factory_imports() -> None:
    pytest.importorskip("langgraph")
    from agents.basic_agent import create_basic_agent

    assert callable(create_basic_agent)


def test_tool_agent_factory_imports() -> None:
    pytest.importorskip("langgraph")
    from agents.tool_agent import create_tool_agent

    assert callable(create_tool_agent)


def test_hitl_agent_factory_imports() -> None:
    pytest.importorskip("langgraph")
    from agents.hitl_agent import create_hitl_agent

    assert callable(create_hitl_agent)


def test_memory_agent_factory_imports() -> None:
    pytest.importorskip("langgraph")
    from agents.memory_agent import create_memory_agent

    assert callable(create_memory_agent)


def test_rag_agent_factory_imports() -> None:
    pytest.importorskip("langgraph")
    pytest.importorskip("faiss")
    from agents.rag_agent import create_rag_agent

    assert callable(create_rag_agent)


def test_mcp_server_imports() -> None:
    pytest.importorskip("mcp")
    import mcp_server

    assert hasattr(mcp_server, "__file__")


def test_basic_agent_format_response_with_string() -> None:
    """``format_response`` must handle plain string output (Ollama-style)."""
    from agents.basic_agent import format_response

    assert format_response("Hello world.").endswith(".")


def test_basic_agent_format_response_with_aimessage_like() -> None:
    """``format_response`` must handle ``AIMessage``-shaped output (Claude/OpenAI)."""
    from agents.basic_agent import format_response

    class FakeAIMessage:
        content = "Hello world. This is two sentences. And here's a third."

    out = format_response(FakeAIMessage())
    # Truncated to two sentences, ends with a period.
    assert out.endswith(".")
    assert "third" not in out


def test_tool_agent_soma_tool() -> None:
    """The ``soma`` tool itself is a pure function and easy to unit-test."""
    pytest.importorskip("langchain_core")
    from agents.tool_agent import soma

    # langchain wraps @tool functions; .invoke is the supported entrypoint.
    assert soma.invoke({"expressao": "3 4"}) == 7.0


def test_tool_agent_soma_rejects_bad_input() -> None:
    pytest.importorskip("langchain_core")
    from agents.tool_agent import soma

    with pytest.raises(ValueError, match="dois números"):
        soma.invoke({"expressao": "1 2 3"})
