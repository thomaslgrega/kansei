from fastapi.testclient import TestClient

from kansei.api import create_app

INDEX = "<!doctype html><title>kansei</title>"


def test_a_client_side_path_gets_the_web_app_and_an_unknown_api_path_gets_json(tmp_path):
    (tmp_path / "index.html").write_text(INDEX)
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "app.js").write_text("console.log('kansei')")
    client = TestClient(create_app(tmp_path))

    pages = [client.get(path) for path in ["/", "/login", "/login?next=%2F", "/tracked/12"]]
    asset = client.get("/assets/app.js")
    api = [client.get(path) for path in ["/api", "/api/nope", "/api/me/nope"]]

    assert [(page.status_code, page.headers["content-type"], page.text) for page in pages] == [
        (200, "text/html; charset=utf-8", INDEX),
    ] * 4
    assert (asset.status_code, asset.text) == (200, "console.log('kansei')")
    assert [(response.status_code, response.json()) for response in api] == [
        (404, {"detail": "Not Found"}),
    ] * 3
