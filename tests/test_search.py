from kansei.search import board_match


def test_a_board_matches_exactly_when_the_query_holds_its_name_or_token_and_partly_when_a_word_starts_with_the_query():
    boards = [
        ("Stripe", "stripe"),
        ("Stripes Inc", "stripes"),
        ("Woven by Toyota", "woven-by-toyota"),
        ("Zetaworks K.K.", "zw-careers"),
        ("ビジョナル株式会社", "visional"),
        ("Cookpad", "cookpad"),
    ]
    queries = [
        "stripe", "STRIPE backend", "woven by toyota", "toyota", "woven by toy", "zw-careers", "zw careers", "zw",
        "ビジョナル", "visional エンジニア", "tripe", "backend", "c++", "c#", "",
    ]

    matched = {
        query: {company: match for company, token in boards if (match := board_match(query, company, token))}
        for query in queries
    }

    assert matched == {
        "stripe": {"Stripe": "exact", "Stripes Inc": "partial"},
        "STRIPE backend": {"Stripe": "exact"},
        "woven by toyota": {"Woven by Toyota": "exact"},
        "toyota": {"Woven by Toyota": "partial"},
        "woven by toy": {"Woven by Toyota": "partial"},
        "zw-careers": {"Zetaworks K.K.": "exact"},
        "zw careers": {"Zetaworks K.K.": "exact"},
        "zw": {"Zetaworks K.K.": "partial"},
        "ビジョナル": {"ビジョナル株式会社": "partial"},
        "visional エンジニア": {"ビジョナル株式会社": "exact"},
        "tripe": {},
        "backend": {},
        "c++": {},
        "c#": {},
        "": {},
    }
