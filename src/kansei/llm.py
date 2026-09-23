from typing import Literal

from openai import AsyncOpenAI
from openai.types.responses import ParsedResponse, ResponseUsage
from pydantic import BaseModel, Field

from kansei.config import settings


class PostingFacts(BaseModel):
    role_summary: str = Field(description="One Sentence: what this person actually builds.")
    seniority: Literal["intern", "junior", "mid", "senior", "staff_plus", "unclear"]
    must_have_skills: list[str] = Field(
        description="Named technologies the posting requires, as written. Empty list if none are named."
    )
    japanese_required: Literal["yes", "no", "unclear"]
    japanese_level: str | None = Field(
        description="The level if the posting states one, e.g. 'N2' or 'business'. Null if unstated."
    )
    remote_allowed: bool

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


PRICE_PER_MTOK = {"input": 0.20, "cached_input": 0.02, "output": 1.20}
CACHE_WRITE_MULTIPLIER = 1.25


def cost_usd(usage: ResponseUsage) -> float:
    input_tokens = usage.input_tokens - usage.input_tokens_details.cached_tokens - usage.input_tokens_details.cache_write_tokens
    input_base_cost = PRICE_PER_MTOK["input"] * input_tokens
    cached_read_cost = PRICE_PER_MTOK["cached_input"] * usage.input_tokens_details.cached_tokens
    cached_write_cost = PRICE_PER_MTOK["input"] * CACHE_WRITE_MULTIPLIER * usage.input_tokens_details.cache_write_tokens
    output_cost = PRICE_PER_MTOK["output"] * usage.output_tokens
    return (input_base_cost + cached_read_cost + cached_write_cost + output_cost) / 1_000_000