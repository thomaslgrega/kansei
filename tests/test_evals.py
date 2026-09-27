from datetime import UTC, datetime

from kansei.evals import LABELS, POSTINGS, FrozenPosting, Label, add_new, load

THEN = datetime(2026, 9, 26, tzinfo=UTC)
LATER = datetime(2026, 10, 3, tzinfo=UTC)


def test_freezing_again_never_changes_a_posting_that_is_already_frozen():
    frozen = [FrozenPosting(url="https://a", title="A", text="必須条件: 日本語 N2", frozen_at=THEN)]
    fetched = [
        FrozenPosting(url="https://a", title="A", text="edited by the company since", frozen_at=LATER),
        FrozenPosting(url="https://b", title="B", text="a new posting", frozen_at=LATER),
    ]

    merged = add_new(frozen, fetched)

    assert [(p.url, p.text, p.frozen_at) for p in merged] == [
        ("https://a", "必須条件: 日本語 N2", THEN),
        ("https://b", "a new posting", LATER),
    ]


def test_every_label_uses_the_models_values_and_names_a_frozen_posting():
    frozen = {p.url for p in load(POSTINGS, FrozenPosting)}
    labels = load(LABELS, Label)
    urls = [label.url for label in labels]

    assert labels, f"no labels in {LABELS}"
    assert len(urls) == len(set(urls)), "a posting is labeled twice"
    assert set(urls) <= frozen, "a label names a posting that isn't frozen"