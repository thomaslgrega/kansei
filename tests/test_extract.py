import asyncio
from types import SimpleNamespace

import httpx
import pytest
from openai.lib._pydantic import to_strict_json_schema

from kansei import extract_one, model_input
from kansei.llm import INSTRUCTIONS, PostingFacts

FACTS = PostingFacts(
    role_summary="Builds payment services.",
    seniority="mid",
    must_have_skills=["Python"],
    japanese_as_written=None,
    japanese_required="not_stated",
    japanese_level="not_stated",
    jlpt="not_stated",
    remote_policy="hybrid",
)


class StubResponses:
    def __init__(self, reply: PostingFacts | None = None):
        self.reply = reply or FACTS
        self.calls: list[dict] = []

    async def parse(self, **kwargs) -> SimpleNamespace:
        self.calls.append(kwargs)
        return SimpleNamespace(output_parsed=self.reply, usage=None)


class StubLLM:
    def __init__(self, responses: StubResponses | None = None):
        self.responses = responses or StubResponses()


async def test_model_input_puts_the_title_above_the_fetched_posting(make_posting, make_board):
    async with make_board("We need a Python engineer in Tokyo.") as http:
        text = await model_input(http, make_posting())

    assert text == "Software Engineer\n\nWe need a Python engineer in Tokyo."


async def test_model_input_skips_the_fetch_when_the_source_already_supplied_the_text(make_posting):
    def explode(request: httpx.Request) -> httpx.Response:
        raise AssertionError(f"should not have fetched {request.url}")

    async with httpx.AsyncClient(transport=httpx.MockTransport(explode)) as http:
        text = await model_input(
            http,
            make_posting(source="lever", token= "woven-by-toyota", description="ロボットのソフトウェア"),
        )

    assert text == "Software Engineer\n\nロボットのソフトウェア"


async def test_extract_one_sends_the_text_to_the_model():
    llm = StubLLM()

    response, seconds = await extract_one(llm, asyncio.Semaphore(1), "Software Engineer\n\nPython")

    assert llm.responses.calls[0]["input"] == "Software Engineer\n\nPython"
    assert llm.responses.calls[0]["instructions"] == INSTRUCTIONS
    assert llm.responses.calls[0]["text_format"] == PostingFacts
    assert response.output_parsed is FACTS
    assert seconds >= 0.0


async def test_extract_one_lets_a_model_failure_escape():
    class Exploding(StubResponses):
        async def parse(self, **kwargs):
            raise httpx.ConnectError("boom")

    llm = StubLLM(Exploding())

    with pytest.raises(httpx.ConnectError):
        await extract_one(llm, asyncio.Semaphore(1), "Software Engineer\n\nPython")


def test_every_field_is_required_so_no_default_can_ever_fire():
    schema = to_strict_json_schema(PostingFacts)

    assert set(schema["required"]) == set(schema["properties"])
    assert schema["additionalProperties"] is False


def test_no_field_carries_a_default_the_model_would_override():
    schema = to_strict_json_schema(PostingFacts)

    defaulted = [name for name, f in schema["properties"].items() if "default" in f]
    assert defaulted == []


def test_every_enum_has_exactly_one_way_to_say_the_posting_is_silent():
    schema = to_strict_json_schema(PostingFacts)
    enums = {name: f["enum"] for name, f in schema["properties"].items() if "enum" in f}

    assert len(enums) == 5
    for name, values in enums.items():
        assert "not_stated" in values, name
        assert not {"unclear", "unknown", "other", "none"} & set(values), name


def test_every_enum_carries_its_decision_rule():
    schema = to_strict_json_schema(PostingFacts)

    missing = [name for name, f in schema["properties"].items() if "enum" in f and not f.get("description")]
    assert missing == []
