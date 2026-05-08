"""Property-based tests com Hypothesis.

Hypothesis gera centenas de inputs aleatórios sob estratégias declaradas e
verifica que invariantes valem em todos eles. Pega bugs em casos limites
que `pytest` baseado em exemplos não enxerga (zero, negativos, NaN,
strings vazias, unicode pesado).
"""

from __future__ import annotations

import pytest

pytest.importorskip("hypothesis")
pytest.importorskip("langchain_core")

from hypothesis import given, settings
from hypothesis import strategies as st

from agents.basic_agent import format_response
from agents.tool_agent import soma

# ── soma — propriedades aritméticas ────────────────────────────────────────


@given(
    a=st.floats(allow_nan=False, allow_infinity=False, min_value=-1e9, max_value=1e9),
    b=st.floats(allow_nan=False, allow_infinity=False, min_value=-1e9, max_value=1e9),
)
@settings(max_examples=200, deadline=None)
def test_soma_commutative(a: float, b: float) -> None:
    """``soma(a, b) == soma(b, a)``."""
    assert soma.invoke({"a": a, "b": b}) == pytest.approx(soma.invoke({"a": b, "b": a}))


@given(
    a=st.floats(allow_nan=False, allow_infinity=False, min_value=-1e9, max_value=1e9),
)
@settings(max_examples=100, deadline=None)
def test_soma_zero_identity(a: float) -> None:
    """``soma(a, 0) == a`` (identidade aditiva)."""
    assert soma.invoke({"a": a, "b": 0.0}) == pytest.approx(a)


@given(
    a=st.floats(allow_nan=False, allow_infinity=False, min_value=-1e6, max_value=1e6),
)
@settings(max_examples=100, deadline=None)
def test_soma_negation(a: float) -> None:
    """``soma(a, -a) == 0`` (inverso aditivo)."""
    assert soma.invoke({"a": a, "b": -a}) == pytest.approx(0.0)


# ── format_response — invariantes ──────────────────────────────────────────


@given(text=st.text(min_size=1, max_size=200))
@settings(max_examples=100, deadline=None)
def test_format_response_always_ends_with_period(text: str) -> None:
    """Qualquer string não-vazia → resultado termina em ``.``."""
    out = format_response(text)
    assert out.endswith(".")


@given(text=st.text(min_size=1, max_size=200))
@settings(max_examples=100, deadline=None)
def test_format_response_no_trailing_newline(text: str) -> None:
    """Resultado nunca contém newlines."""
    out = format_response(text)
    assert "\n" not in out


@given(text=st.text(min_size=1, max_size=200))
@settings(max_examples=100, deadline=None)
def test_format_response_idempotent_on_clean_period(text: str) -> None:
    """Aplicar ``format_response`` duas vezes gera o mesmo resultado.

    A operação é uma forma normal: depois da primeira aplicação, o
    output já está no formato esperado, então uma segunda aplicação
    não muda nada.
    """
    once = format_response(text)
    twice = format_response(once)
    assert once == twice


@given(text=st.text(min_size=1, max_size=200))
@settings(max_examples=100, deadline=None)
def test_format_response_at_most_two_sentences(text: str) -> None:
    """O output tem no máximo 1 ponto interno (i.e., ≤ 2 frases delimitadas).

    Implementação: split em ``". "`` deve dar no máximo 2 elementos.
    Casos limites com pontos sem espaço (ex: ``"3.14"``) podem ter mais —
    isso é uma propriedade frouxa.
    """
    out = format_response(text)
    sentences = out.split(". ")
    assert len(sentences) <= 2


# ── FakeChatModel — propriedade de fila ────────────────────────────────────


@given(messages=st.lists(st.text(min_size=1, max_size=50), min_size=1, max_size=20))
@settings(max_examples=50, deadline=None)
def test_fake_chat_model_consumes_in_order(messages: list[str]) -> None:
    """O FakeChatModel devolve respostas exatamente na ordem de ``responses``."""
    from langchain_core.messages import HumanMessage

    from tests.fakes import FakeChatModel

    fake = FakeChatModel()
    fake.responses = list(messages)

    for expected in messages:
        result = fake.invoke([HumanMessage(content="x")])
        assert result.content == expected


@given(n=st.integers(min_value=0, max_value=20))
@settings(max_examples=20, deadline=None)
def test_fake_chat_model_raises_when_exhausted(n: int) -> None:
    """Após ``n`` respostas pré-definidas, a (n+1)-ésima invocação levanta."""
    from langchain_core.messages import HumanMessage

    from tests.fakes import FakeChatModel

    fake = FakeChatModel()
    fake.responses = ["x"] * n

    for _ in range(n):
        fake.invoke([HumanMessage(content="q")])

    with pytest.raises(RuntimeError, match="sem respostas"):
        fake.invoke([HumanMessage(content="q")])
