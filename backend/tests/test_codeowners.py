from app.services.codeowners import suggested_reviewers_from_codeowners


def test_codeowners_suggest() -> None:
    text = "src/foo.ts @alice\n"
    r = suggested_reviewers_from_codeowners(
        text,
        ["src/foo.ts"],
    )
    assert "alice" in r
