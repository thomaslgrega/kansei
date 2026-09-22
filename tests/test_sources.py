from kansei.sources import from_greenhouse, from_lever


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
    "descriptionPlain": "Job description"
}


def test_the_two_adapters_produce_exactly_the_same_keys():
    assert from_greenhouse(GREENHOUSE_RAW, "stripe").keys() == from_lever(LEVER_RAW, "woven-by-toyota").keys()


def test_from_lever_maps_the_fields_that_have_different_names():
    posting = from_lever(LEVER_RAW, "woven-by-toyota")

    assert posting["id"] == "84925f74-a6aa-4b90-a92b-7006f1f88779"
    assert posting["title"] == "バックエンドエンジニア・Robot Platform Software"
    assert posting["location"] == "東京都中央区"
    assert posting["source"] == "lever"


def test_from_greenhouse_stringifies_the_integer_id():
    assert from_greenhouse(GREENHOUSE_RAW, "stripe")["id"] == "4419"