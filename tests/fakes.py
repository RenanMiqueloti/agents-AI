"""Fakes para testes — substitutos LangChain-compatíveis sem network.

Padrão: cada fake aceita uma fila de respostas pré-determinadas e a consome
por chamada. Permite testar fluxos com decisões variadas (ex: HITL com
tool_calls na 1ª invocação e content puro na 2ª) sem mock complexo.

Componentes:

- ``FakeChatModel`` — substitui ``BaseChatModel``. Aceita lista de
  ``AIMessage`` (ou strings convertidas) e retorna na ordem em cada
  ``_generate``. Suporta ``bind_tools`` (no-op que mantém a fila).
- ``FakeEmbeddings`` — embedding determinístico por hash. 8 dimensões
  bastam pra similaridade ser estável em testes.
- ``make_fake_retriever`` — fabrica um ``Runnable`` que ignora a query
  e retorna uma lista fixa de ``Document``.
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from typing import Any

from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.runnables import RunnableLambda
from pydantic import Field


class FakeChatModel(BaseChatModel):
    """Chat model scriptado pra testes.

    Cada chamada de ``invoke`` consome a próxima resposta de ``responses``.
    Se a fila esvaziar, levanta ``RuntimeError`` — assim um teste com mais
    chamadas que mocks falha explicitamente em vez de silenciosamente.

    Atributos:
        responses: Fila de mensagens (``AIMessage`` ou strings — strings
            viram ``AIMessage(content=str)``). Pode incluir ``tool_calls``
            para simular chamadas de ferramenta.
        calls: Lista de chamadas recebidas (sequência de mensagens), útil
            pra asserções tipo "o agente passou pelo prompt esperado".
    """

    responses: list[Any] = Field(default_factory=list)
    calls: list[list[BaseMessage]] = Field(default_factory=list)

    @property
    def _llm_type(self) -> str:
        return "fake"

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        self.calls.append(list(messages))
        if not self.responses:
            raise RuntimeError(
                "FakeChatModel sem respostas restantes. "
                "Adicione mais mensagens em `responses` ou ajuste o teste."
            )

        next_response = self.responses.pop(0)
        if isinstance(next_response, str):
            msg = AIMessage(content=next_response)
        elif isinstance(next_response, AIMessage):
            msg = next_response
        elif isinstance(next_response, BaseMessage):
            msg = AIMessage(content=str(next_response.content))
        else:
            msg = AIMessage(content=str(next_response))

        return ChatResult(generations=[ChatGeneration(message=msg)])

    def bind_tools(self, tools: Sequence[Any], **kwargs: Any) -> FakeChatModel:
        """Stub de ``bind_tools`` — devolve ``self`` mantendo a fila.

        As respostas já carregam ``tool_calls`` quando relevantes; a versão
        real de ``bind_tools`` insere o schema das ferramentas no prompt,
        comportamento que não interessa pra testes determinísticos.
        """
        return self


class FakeEmbeddings(Embeddings):
    """Embeddings determinísticas — hash MD5 mapeado em vetor de 8 floats.

    Não capturam semântica, mas duas chamadas com o mesmo texto retornam
    exatamente o mesmo vetor. Suficiente para testar pipelines de RAG e
    índices vetoriais sem depender de Ollama.
    """

    dim: int = 8

    def embed_query(self, text: str) -> list[float]:
        digest = hashlib.md5(text.encode("utf-8")).digest()
        return [b / 255.0 for b in digest[: self.dim]]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_query(t) for t in texts]


def make_fake_retriever(documents: list[Document]) -> RunnableLambda:
    """Retorna um ``Runnable`` que ignora a query e devolve ``documents``.

    Útil pra testar pipelines RAG: a chain passa a query pelo retriever,
    aqui o retriever só ecoa um conjunto fixo de docs pro próximo nó.
    """

    def _retrieve(_query: str) -> list[Document]:
        return list(documents)

    return RunnableLambda(_retrieve)
