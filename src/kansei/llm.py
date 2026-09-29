from typing import Literal

from openai import AsyncOpenAI
from openai.types.responses import ParsedResponse, ResponseUsage
from pydantic import BaseModel, Field

from kansei.config import settings

Seniority = Literal["intern", "junior", "mid", "senior", "staff_plus", "not_stated"]
JapaneseRequired = Literal["required", "preferred", "not_required", "not_stated"]
JapaneseLevel = Literal["native", "business", "conversational", "basic", "not_stated"]
Jlpt = Literal["N1", "N2", "N3", "N4", "N5", "not_stated"]
RemotePolicy = Literal["remote", "hybrid", "onsite", "not_stated"]


class PostingFacts(BaseModel):
    role_summary: str = Field(description="One sentence in English, whatever language the posting is in: what this person actually builds.")
    seniority: Seniority = Field(
        description=(
            "The level the title or text names in words: 'Junior'/ジュニア, 'Senior'/シニア, "
            "'Staff' or 'Principal' for staff_plus. Years of experience alone do not set a level, "
            "and neither does 'Lead'. not_stated if no level word appears."
        )
    )
    must_have_skills: list[str] = Field(
        description=(
            "Named software the posting lists as required: languages, frameworks, libraries, "
            "tools, databases, platforms and cloud services, i.e. things you could install, run "
            "or sign up for. Only from the required list (必須条件, 'Minimum qualifications', "
            "'What you'll need', 'Requirements'), never from nice-to-haves, duties or boilerplate. "
            "Every name on a required line counts, including alternatives ('X or Y', または), "
            "examples ('e.g.', 'such as', 例, など) and the team's stack ('we use X'). "
            "Not kinds of thing (cloud, containers, CI/CD, infrastructure as code, shell "
            "scripting, machine learning, LLM APIs), standards or protocols (ISO 26262, CAN), "
            "methods (Agile, MLOps), or human languages and their tests (Japanese, JLPT, TOEIC). "
            "One name per item, copied exactly as the posting writes it, typos included. "
            "Empty list if the required list names none."
        )
    )
    japanese_as_written: str | None = Field(
        description=(
            "The posting's own words about the candidate's Japanese ability, copied exactly. "
            "Null if it says nothing about the candidate's Japanese."
        )
    )
    japanese_required: JapaneseRequired = Field(
        description=(
            "required: listed as a requirement (e.g. 'Minimum qualifications', 必須条件). "
            "Slashes between two languages (e.g. 'Business-level English/Japanese') means both are required. "
            "preferred: listed only as a plus (e.g. 'Nice to have', 歓迎条件). "
            "A plus is preferred even when the posting adds that it is not required. "
            "not_required: only for postings that say Japanese isn't needed and don't count it in your favour. "
            "not_stated: it says nothing about the candidate's Japanese. Mentions of Japanese "
            "customers, companies, holidays or résumés are not about the candidate's Japanese."
        )
    )
    japanese_level: JapaneseLevel = Field(
        description=(
            "The level named in words. "
            "native: 'native'/ネイティブ. "
            "business: 'business level', 'fluent', ビジネスレベル, 流暢. "
            "conversational: 'conversational', 'daily conversation', 日常会話. "
            "basic: 'basic'/基礎. "
            "If one phrase names two levels, take the higher. "
            "not_stated if no level word appears, even when Japanese is required. "
            "A JLPT level alone does not set this field."
        )
    )
    jlpt: Jlpt = Field(
        description=(
            "The JLPT level named, including 'or equivalent'/相当 and 'or higher'/以上 forms. "
            "not_stated if none is named."
        )
    )
    remote_policy: RemotePolicy = Field(
        description=(
            "remote: no office attendance required. "
            "hybrid: some office days required (e.g. 'the office 3 days per week', 週3日出社). "
            "onsite: office or site every working day. "
            "not_stated: the posting does not say. "
            "'Hybrid' describing infrastructure, such as "
            "hybrid cloud, is not a work policy. Where the candidate may live is a different "
            "question and does not change this field."
        )
    )

INSTRUCTIONS = """You read job postings for a software engineer who lives in Japan.
Extract only what the posting actually states. Do not infer, and do not fill a
field from general knowledge about the company."""


async def extract(llm: AsyncOpenAI, posting: str) -> ParsedResponse[PostingFacts]:
    return await llm.responses.parse(
        model=settings.openai_model,
        instructions=INSTRUCTIONS,
        input=posting,
        text_format=PostingFacts,
    )


PRICE_PER_MTOK = {
    "gpt-5.6-luna": {"input": 0.20, "cached_input": 0.02, "cache_write": 0.25, "output": 1.20},
    "gpt-6-luna": {"input": 0.10, "cached_input": 0.01, "cache_write": 0.125, "output": 0.50},
}

LONG_CONTEXT_INPUT_TOKENS = 272_000

def cost_usd(usage: ResponseUsage, model: str) -> float:
    if usage.input_tokens > LONG_CONTEXT_INPUT_TOKENS:
        raise ValueError(
            f"{usage.input_tokens:,} input tokens is over the {LONG_CONTEXT_INPUT_TOKENS:,} "
            "long-context threshold, which PRICE_PER_MTOK does not price"
        )
    price = PRICE_PER_MTOK[model]
    input_tokens = usage.input_tokens - usage.input_tokens_details.cached_tokens - usage.input_tokens_details.cache_write_tokens
    input_base_cost = price["input"] * input_tokens
    cached_read_cost = price["cached_input"] * usage.input_tokens_details.cached_tokens
    cached_write_cost = price["cache_write"] * usage.input_tokens_details.cache_write_tokens
    output_cost = price["output"] * usage.output_tokens
    return (input_base_cost + cached_read_cost + cached_write_cost + output_cost) / 1_000_000