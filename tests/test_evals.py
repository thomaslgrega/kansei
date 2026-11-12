import sys
from datetime import UTC, datetime

import pytest

from kansei import evals
from kansei.evals import (
    DUTIES,
    LABELS,
    MANIFEST,
    POSTINGS,
    RUNS,
    FrozenPosting,
    Label,
    ManifestEntry,
    SkillDiff,
    add_new,
    compare_skills,
    load,
    manifest_entry,
    per_board,
    per_specialty,
    precision_recall_f1,
    print_posting,
    score,
    skill_misses,
    specialty_misses,
)

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
    frozen = {entry.url for entry in load(MANIFEST, ManifestEntry)}
    labels = load(LABELS, Label)
    urls = [label.url for label in labels]

    assert labels, f"no labels in {LABELS}"
    assert len(urls) == len(set(urls)), "a posting is labeled twice"
    assert set(urls) <= frozen, "a label names a posting that isn't frozen"


def test_the_local_postings_are_exactly_the_text_the_manifest_records():
    if not POSTINGS.exists():
        pytest.skip(f"{POSTINGS.name} is not in the repo; the posting text is kept private")

    postings = load(POSTINGS, FrozenPosting)

    assert [manifest_entry(p) for p in postings] == load(MANIFEST, ManifestEntry)


def answers(url: str, **fields: str | list[str]) -> Label:
    return Label(**{
        "url": url,
        "seniority": "not_stated",
        "japanese_required": "not_stated",
        "japanese_level": "not_stated",
        "jlpt": "not_stated",
        "remote_policy": "not_stated",
        **fields,
    })

def test_score_pairs_each_prediction_with_its_label_by_url_not_by_position():
    labels = [answers("https://a", jlpt="N1"), answers("https://b")]
    predictions = [answers("https://b"), answers("https://a", jlpt="N2")]

    wrong = score(labels, predictions)

    assert wrong == {
        "seniority": [],
        "japanese_required": [],
        "japanese_level": [],
        "jlpt": ["https://a"],
        "remote_policy": [],
    }


def test_score_refuses_a_run_that_is_missing_a_labeled_posting():
    labels = [answers("https://a"), answers("https://b")]

    with pytest.raises(ValueError, match=r"^no prediction for https://b$"):
        score(labels, [answers("https://a")])


def test_every_labeled_skill_is_written_in_its_posting():
    if not POSTINGS.exists():
        pytest.skip(f"{POSTINGS.name} is not in the repo; the posting text is kept private")

    text = {p.url: p.text for p in load(POSTINGS, FrozenPosting)}
    not_found = [
        (label.url, skill)
        for label in load(LABELS, Label)
        for skill in label.must_have_skills or []
        if skill not in text[label.url]
    ]

    assert not_found == []


def test_skills_score_as_sets_of_exact_names_and_skip_unlabeled_postings():
    labels = [
        answers("https://a", must_have_skills=["Python", "Go", "Basel"]),
        answers("https://b", must_have_skills=[]),
        answers("https://c"),
    ]
    predictions = [
        answers("https://a", must_have_skills=["Go", "Python", "Bazel"]),
        answers("https://b", must_have_skills=["Google Meet"]),
        answers("https://c", must_have_skills=["Rust"]),
    ]

    diffs = compare_skills(labels, predictions)

    assert diffs == {
        "https://a": SkillDiff(found={"Python", "Go"}, extra={"Bazel"}, missed={"Basel"}),
        "https://b": SkillDiff(found=set(), extra={"Google Meet"}, missed=set()),
    }
    assert precision_recall_f1(list(diffs.values())) == pytest.approx((1/2, 2/3, 4/7))


def test_specialties_score_by_exact_set_and_by_specialty_skipping_unlabeled_postings():
    labels = [
        answers("https://a", specialties=["backend"]),
        answers("https://b", specialties=["backend", "frontend"]),
        answers("https://c", specialties=["management", "mobile"]),
        answers("https://d", specialties=["mobile"]),
        answers("https://e"),
        answers("https://f", specialties=[]),
        answers("https://g", specialties=[]),
    ]
    predictions = [
        answers("https://a", specialties=["backend"]),
        answers("https://b", specialties=["backend"]),
        answers("https://c", specialties=["mobile", "management"]),
        answers("https://d", specialties=["backend", "mobile"]),
        answers("https://e", specialties=["qa"]),
        answers("https://f", specialties=[]),
        answers("https://g", specialties=["qa"]),
    ]

    by_specialty = per_specialty(labels, predictions)

    assert specialty_misses(labels, predictions) == ["https://b", "https://d", "https://g"]
    assert by_specialty == {
        "backend": SkillDiff(found={"https://a", "https://b"}, extra={"https://d"}, missed=set()),
        "frontend": SkillDiff(found=set(), extra=set(), missed={"https://b"}),
        "mobile": SkillDiff(found={"https://c", "https://d"}, extra=set(), missed=set()),
        "management": SkillDiff(found={"https://c"}, extra=set(), missed=set()),
        "qa": SkillDiff(found=set(), extra={"https://g"}, missed=set()),
    }
    assert {s: precision_recall_f1([diff])[:2] for s, diff in by_specialty.items()} == pytest.approx({
        "backend": (2/3, 1.0),
        "frontend": (0.0, 0.0),
        "mobile": (1.0, 1.0),
        "management": (1.0, 1.0),
        "qa": (0.0, 0.0),
    })


def test_a_hand_written_fullstack_label_is_also_frontend_and_backend():
    assert Label.model_validate_json(
        '{"url": "https://a", "seniority": "not_stated", "japanese_required": "not_stated", '
        '"japanese_level": "not_stated", "jlpt": "not_stated", "remote_policy": "not_stated", '
        '"specialties": ["fullstack"]}'
    ).specialties == ["backend", "frontend", "fullstack"]


def test_skill_misses_counts_runs_per_posting_not_names():
    labels = [
        answers("https://a", must_have_skills=["C", "C++"]),
        answers("https://b", must_have_skills=["Go"]),
        answers("https://c"),
    ]
    split = answers("https://a", must_have_skills=["C", "C++"])
    joined = answers("https://a", must_have_skills=["C/C++"])
    only_c = answers("https://a", must_have_skills=["C"])
    go = answers("https://b", must_have_skills=["Go"])
    go_shell = answers("https://b", must_have_skills=["Go", "Shell"])
    rust = answers("https://c", must_have_skills=["Rust"])

    runs = [[joined, go, rust], [split, go_shell, rust], [only_c, go, rust]]
    assert skill_misses(labels, runs) == {"https://a": 2, "https://b": 1}


def test_per_board_keeps_the_first_k_of_each_board_in_order(make_posting):
    jobs = [
        make_posting(token="a", id="a1"),
        make_posting(token="b", id="b1"),
        make_posting(token="a", id="a2"),
        make_posting(token="a", id="a3"),
        make_posting(token="c", id="c1"),
        make_posting(token="b", id="b2"),
        make_posting(token="b", id="b3"),
    ]

    picked = per_board(jobs, k=2)

    assert [job.id for job in picked] == ["a1", "b1", "a2", "c1", "b2"]


def test_no_dev_run_has_seen_a_test_posting():
    test_set = {entry.url for entry in load(MANIFEST, ManifestEntry) if entry.split == "test"}
    seen = {
        prediction.url
        for path in RUNS.glob("*.jsonl")
        for prediction in load(path, Label)
    }

    assert seen & test_set == set()


def test_specialty_labeling_marks_only_the_duties_headings(capsys):
    posting = FrozenPosting(
        url="https://a",
        title="Software Engineer",
        text=(
            "Software Engineer\n"
            "【具体的な業務内容】\n"
            "決済システムのバックエンド開発\n"
            "What You'll Do:\n"
            "Build our iOS app.\n"
            "必須条件\n"
            "業務内容に関わる3年以上の経験\n"
            "Nice to have: React"
        ),
        frozen_at=THEN,
    )

    print_posting(posting, DUTIES)

    assert capsys.readouterr().out.splitlines() == [
        "",
        "=" * 72,
        "  Software Engineer",
        "» 【具体的な業務内容】",
        "  決済システムのバックエンド開発",
        "» What You'll Do:",
        "  Build our iOS app.",
        "  必須条件",
        "  業務内容に関わる3年以上の経験",
        "  Nice to have: React",
        "",
        "https://a",
    ]


def test_specialties_command_labels_the_urls_it_names(monkeypatch):
    calls = []
    monkeypatch.setattr(sys, "argv", ["kansei-eval", "specialties", "https://a"])
    monkeypatch.setattr(evals, "label_specialties", calls.append)
    evals.main()
    assert calls == [["https://a"]]


@pytest.mark.parametrize(("args", "expected"), [
    (["label"], ([], "dev")),
    (["label", "test"], ([], "test")),
    (["label", "https://a"], (["https://a"], "dev")),
], ids=["label", "label test", "label URL"])
def test_label_command_reaches_the_split_it_names(monkeypatch, args, expected):
    calls = []
    monkeypatch.setattr(sys, "argv", ["kansei-eval", *args])
    monkeypatch.setattr(evals, "label", lambda urls, split="dev": calls.append((urls, split)))
    evals.main()
    assert calls == [expected]
