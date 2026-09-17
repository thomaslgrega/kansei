from openai import AsyncOpenAI
from openai.types.responses import Response, ResponseUsage

from kansei.config import settings

INSTRUCTIONS = """You read job postings for a software engineer who lives in Japan.
Reply in English with exactly three lines:
Role: <one sentence>
Must-Have: <comma-separated>
Japanese Required: <yes / no / unclear, and the level if stated>"""


async def summarise(llm: AsyncOpenAI, posting: str) -> Response:
    return await llm.responses.create(
        model=settings.openai_model,
        instructions=INSTRUCTIONS,
        input=posting,
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