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


PRICE_PER_MTOK = {
    "gpt-5.6-luna": {"input": 0.20, "cached_input": 0.02, "cache_write": 0.25, "output": 1.20},
    "gpt-6-luna": {"input": 0.10, "cached_input": 0.01, "cache_write": 0.125, "output": 0.50},
}

LONG_CONTEXT_INPUT_TOKENS = 272_000

def cost_usd(usage: ResponseUsage, model: str) -> float:
    if usage.input_tokens > LONG_CONTEXT_INPUT_TOKENS:
        raise ValueError(
            f"{usage.input_tokens:,} "
            "long-context threshold, which PRICE_PER_MTOK does not price"
        )
    price = PRICE_PER_MTOK[model]
    input_tokens = usage.input_tokens - usage.input_tokens_details.cached_tokens - usage.input_tokens_details.cache_write_tokens
    input_base_cost = price["input"] * input_tokens
    cached_read_cost = price["cached_input"] * usage.input_tokens_details.cached_tokens
    cached_write_cost = price["cache_write"] * usage.input_tokens_details.cache_write_tokens
    output_cost = price["output"] * usage.output_tokens
    return (input_base_cost + cached_read_cost + cached_write_cost + output_cost) / 1_000_000