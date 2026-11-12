import asyncio
import json
from types import SimpleNamespace

import httpx
import pytest
from openai.lib._pydantic import to_strict_json_schema

from kansei import extract_one, model_input
from kansei.llm import INSTRUCTIONS, PostingFacts, normalize_specialties

FACTS = PostingFacts(
    role_summary="Builds payment services.",
    specialties=["backend"],
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


class ParsingResponses(StubResponses):
    def __init__(self, answer: dict):
        super().__init__()
        self.answer = answer

    async def parse(self, **kwargs) -> SimpleNamespace:
        self.calls.append(kwargs)
        parsed = kwargs["text_format"].model_validate_json(json.dumps(self.answer))
        return SimpleNamespace(output_parsed=parsed, usage=None)


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


def test_the_model_gets_the_specialties_context_md_defines_and_the_title_first_rule():
    schema = to_strict_json_schema(PostingFacts)

    assert schema["properties"]["specialties"] == {
        "title": "Specialties",
        "type": "array",
        "items": {
            "type": "string",
            "enum": [
                "backend", "frontend", "fullstack", "mobile", "infrastructure", "data", "ml",
                "security", "qa", "embedded", "management", "customer_facing",
            ],
        },
        "description": (
            "The kinds of engineering the role is for. Take every specialty the title names, and "
            "then stop: 'iOS Engineer' is mobile, whatever the duties say. Only when the title names "
            "no area of work, just management, customer-facing or nothing at all, add the areas the "
            "duties describe: 'Software Engineer' may be backend, or backend and frontend; "
            "'Engineering Manager' is management plus its duties' areas; 'Engineering Manager, "
            "Payments Backend' is management and backend. infrastructure: SRE, platform, DevOps, "
            "cloud, network. data: data engineering and analytics. ml: machine learning and AI. "
            "qa: testing and quality. embedded: firmware and software on devices. management: "
            "managing engineers. customer_facing: solutions, sales, support and field engineers. "
            "Empty list if none of these fits, including a role that is not engineering, such as "
            "事業開発."
        ),
    }


async def test_extract_one_stores_the_specialties_the_model_answers():
    answer = FACTS.model_dump(mode="json") | {"specialties": ["management", "fullstack"]}
    llm = StubLLM(ParsingResponses(answer))

    response, _ = await extract_one(llm, asyncio.Semaphore(1), "Engineering Manager\n\nLead the web team.")

    call = llm.responses.calls[0]
    assert (call["input"], call["instructions"], call["text_format"]) == (
        "Engineering Manager\n\nLead the web team.", INSTRUCTIONS, PostingFacts
    )
    assert response.output_parsed.model_dump(mode="json")["specialties"] == [
        "backend", "frontend", "fullstack", "management"
    ]


@pytest.mark.parametrize(("answer", "stored"), [
    (["fullstack"], ["backend", "frontend", "fullstack"]),
    (["frontend", "fullstack", "backend", "fullstack"], ["backend", "frontend", "fullstack"]),
    (["mobile", "fullstack"], ["backend", "frontend", "fullstack", "mobile"]),
    (["frontend", "backend"], ["backend", "frontend"]),
    ([], []),
], ids=["fullstack alone", "repeated", "with another", "frontend and backend stay apart", "other"])
def test_fullstack_is_also_frontend_and_backend_each_once_in_schema_order(answer, stored):
    assert normalize_specialties(answer) == stored
