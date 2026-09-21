import asyncio
from types import SimpleNamespace

import httpx
import pytest

from kansei import summarize_one
from kansei.llm import INSTRUCTIONS


class StubResponses:
    def __init__(self, reply: str = "Role: backend\nMust-Have: Python\nJapanese Required: no"):
        self.reply = reply
        self.calls: list[dict] = []

    async def create(self, **kwargs) -> SimpleNamespace:
        self.calls.append(kwargs)
        return SimpleNamespace(output_text=self.reply, usage=None)


class StubLLM:
    def __init__(self, responses: StubResponses | None = None):
        self.responses = responses or StubResponses()


async def test_summarize_one_sends_the_fetched_posting_to_the_model(make_posting, make_board):
    llm = StubLLM()

    async with make_board("We need a Python engineer in Tokyo.") as http:
        response, seconds = await summarize_one(
            http, llm, asyncio.Semaphore(1), "stripe", make_posting()
        )

    assert llm.responses.calls[0]["input"] == "We need a Python engineer in Tokyo."
    assert llm.responses.calls[0]["instructions"] == INSTRUCTIONS
    assert response.output_text.startswith("Role:")
    assert seconds >= 0.0


async def test_summarize_one_lets_a_model_failure_escape(make_posting, make_board):
    class Exploding(StubResponses):
        async def create(self, **kwargs):
            raise httpx.ConnectError("boom")

    llm = StubLLM(Exploding())

    async with make_board() as http:
        with pytest.raises(httpx.ConnectError):
            await summarize_one(
                http, llm, asyncio.Semaphore(1), "stripe", make_posting()
            )