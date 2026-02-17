"""Basic app construction smoke test."""

from infinity_film_studio.app import create_app


def test_app_constructs():
    app = create_app()
    assert "ai_client" in app
    assert "prompts" in app
    controllers = app.get("controllers")
    assert controllers
    assert {"script", "video", "storyboard"}.issubset(set(controllers.keys()))
