import pytest

from openai.types.responses import ResponseUsage
from openai.types.responses.response_usage import InputTokensDetails, OutputTokensDetails

from kansei.llm import cost_usd


def usage(*, fresh: int, cached: int = 0, written: int = 0, output: int) -> ResponseUsage:
    return ResponseUsage(
        input_tokens=fresh + cached + written,
        input_tokens_details=InputTokensDetails(cached_tokens=cached, cache_write_tokens=written),
        output_tokens=output,
        output_tokens_details=OutputTokensDetails(reasoning_tokens=0),
        total_tokens=fresh + written + output,
    )


def test_cost_usd_prices_a_cold_call():
    assert cost_usd(usage(fresh=1785, output=76)) == pytest.approx(0.0004482)


def test_cost_usd_does_not_charge_cached_tokens_at_the_full_rate():
    cold = cost_usd(usage(fresh=2000, output=100))
    warm = cost_usd(usage(fresh=1000, cached=1000, output=100))
    assert warm < cold


def test_cost_usd_splits_every_input_token_into_exactly_one_bucket():
    assert cost_usd(usage(fresh=500, cached=1000, written=500, output=100)) == pytest.approx(0.000365)