import pytest

from kansei.sources import from_greenhouse, from_lever, html_to_text

GREENHOUSE_RAW = {
    "id": 4419,
    "title": "software engineer",
    "absolute_url": "https://example.com/1",
    "updated_at": "2026-09-12T13:25:25-04:00",
    "location": {"name": "Tokyo"},
}
LEVER_RAW = {
    "id": "84925f74-a6aa-4b90-a92b-7006f1f88779",
    "text": "バックエンドエンジニア・Robot Platform Software",
    "hostedUrl": "https://example.com/1",
    "createdAt": 1788231211096,
    "categories": {"location": "東京都中央区"},
    "descriptionPlain": "ウーブン・バイ・トヨタについて",
    "lists": [
        {"text": "必須条件", "content": "<ul><li>Pythonでの開発経験3年以上</li></ul>"},
        {"text": "歓迎条件", "content": "<ul><li>英語でのコミュニケーション</li></ul>"},
    ],
    "additionalPlain": "応募について",
}


def test_the_two_adapters_produce_exactly_the_same_keys():
    assert from_greenhouse(GREENHOUSE_RAW, "stripe").keys() == from_lever(LEVER_RAW, "woven-by-toyota").keys()


def test_from_lever_maps_the_fields_that_have_different_names():
    posting = from_lever(LEVER_RAW, "woven-by-toyota")

    assert posting["id"] == "84925f74-a6aa-4b90-a92b-7006f1f88779"
    assert posting["title"] == "バックエンドエンジニア・Robot Platform Software"
    assert posting["location"] == "東京都中央区"
    assert posting["source"] == "lever"

def test_from_lever_sends_the_requirements_not_just_the_company_blurd():
    description = from_lever(LEVER_RAW, "woven-by-toyota")["description"]

    assert "必須条件" in description
    assert "Pythonでの開発経験3年以上" in description
    assert "<li>" not in description


def test_from_greenhouse_stringifies_the_integer_id():
    assert from_greenhouse(GREENHOUSE_RAW, "stripe")["id"] == "4419"


@pytest.mark.parametrize(
    ("fragment", "expected"),
    [
        ("<p>Python</p><p>Go</p>", "Python\nGo"),
        ("<ul><li>3 years of Python</li><li>Business Japanese</li></ul>",
         "3 years of Python\nBusiness Japanese"),
        ("<div>R&amp;D team in <b>Tokyo</b></div>", "R&D team in Tokyo"),
        ("  <p>   Tokyo   </p>  ", "Tokyo"),
    ],
)
def test_html_to_text_keeps_the_words_and_drops_the_markup(fragment, expected):
    assert html_to_text(fragment) == expected