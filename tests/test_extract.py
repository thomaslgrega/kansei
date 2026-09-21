from openai.lib._pydantic import to_strict_json_schema
from types import SimpleNamespace

import asyncio
import httpx
import pytest

from kansei import extract_one
from kansei.llm import INSTRUCTIONS, PostingFacts


class StubResponses:
    def __init__(self, reply: str = "Role: backend\nMust-Have: Python\nJapanese Required: no"):
        self.reply = reply
        self.calls: list[dict] = []

    async def parse(self, **kwargs) -> SimpleNamespace:
        self.calls.append(kwargs)
        return SimpleNamespace(output_text=self.reply, usage=None)


class StubLLM:
    def __init__(self, responses: StubResponses | None = None):
        self.responses = responses or StubResponses()


async def test_extract_one_sends_the_fetched_posting_to_the_model(make_posting, make_board):
    llm = StubLLM()

    async with make_board("We need a Python engineer in Tokyo.") as http:
        response, seconds = await extract_one(
            http, llm, asyncio.Semaphore(1), "stripe", make_posting()
        )

    assert llm.responses.calls[0]["input"] == "We need a Python engineer in Tokyo."
    assert llm.responses.calls[0]["instructions"] == INSTRUCTIONS
    assert llm.responses.calls[0]["text_format"] == PostingFacts
    assert response.output_text.startswith("Role:")
    assert seconds >= 0.0


async def test_extract_one_lets_a_model_failure_escape(make_posting, make_board):
    class Exploding(StubResponses):
        async def parse(self, **kwargs):
            raise httpx.ConnectError("boom")

    llm = StubLLM(Exploding())

    async with make_board() as http:
        with pytest.raises(httpx.ConnectError):
            await extract_one(
                http, llm, asyncio.Semaphore(1), "stripe", make_posting()
            )


def test_every_field_is_required_so_no_default_can_ever_fire():
    schema = to_strict_json_schema(PostingFacts)

    assert set(schema["required"]) == set(schema["properties"])
    assert schema["additionalProperties"] is False


def test_no_field_carries_a_default_the_model_would_override():
    schema = to_strict_json_schema(PostingFacts)

    defaulted = [name for name, f in schema["properties"].items() if "default" in f]
    assert defaulted == []
