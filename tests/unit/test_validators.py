"""Unit tests for validators. No fixtures, no markers needed."""
from scaffold.validators import (
    contains_all,
    contains_none,
    fields_match,
    fields_match_report,
    jaccard,
    category_for_error,
)


def test_contains_all_case_insensitive():
    assert contains_all("Red has hex #FF0000", ["red", "#FF0000"])
    assert contains_all("Red has hex #FF0000", ["RED", "hex"])
    assert not contains_all("Red has hex #FF0000", ["blue"])


def test_contains_all_empty_text():
    assert not contains_all("", ["x"])
    assert contains_all("anything", [])


def test_contains_none_forbidden_tokens():
    assert contains_none("Red is here", ["blue", "green"])
    assert not contains_none("Blue is here", ["blue"])
    assert contains_none("", ["anything"])


def test_jaccard_identical():
    assert jaccard(["hello world", "hello world"]) == 1.0


def test_jaccard_disjoint():
    score = jaccard(["red blue", "green yellow"])
    assert 0.0 <= score < 0.5


def test_jaccard_partial_overlap():
    score = jaccard(["red blue", "red green"])
    assert 0.0 < score < 1.0


def test_jaccard_single_input():
    assert jaccard(["only one"]) == 1.0


def test_jaccard_empty_inputs():
    assert jaccard([]) == 1.0
    assert jaccard(["", ""]) == 1.0


def test_fields_match_exact():
    actual = {"name": "red", "hex": "#FF0000"}
    assert fields_match(actual, {"name": "red", "hex": "#FF0000"})


def test_fields_match_ignores_extras():
    actual = {"name": "red", "hex": "#FF0000", "extra": "ignored"}
    assert fields_match(actual, {"name": "red", "hex": "#FF0000"})


def test_fields_match_missing_field():
    actual = {"name": "red"}
    assert not fields_match(actual, {"name": "red", "hex": "#FF0000"})


def test_fields_match_report_returns_per_field():
    actual = {"name": "red", "hex": "#FFFFFF"}
    report = fields_match_report(actual, {"name": "red", "hex": "#000000"})
    assert report == {"name": True, "hex": False}


def test_category_for_error_none():
    assert category_for_error(None) is None


def test_category_for_error_timeout():
    assert category_for_error(TimeoutError("x")) == "timeout"


def test_category_for_error_client():
    # Real HTTP-style exceptions.
    from scaffold.api_adapter import APIClientError
    assert category_for_error(APIClientError(400, "/x", "bad request")) == "client_error"


def test_category_for_error_server():
    from scaffold.api_adapter import APIServerError
    assert category_for_error(APIServerError(500, "/x", "internal")) == "server_error"


def test_category_for_error_auth():
    from scaffold.api_adapter import APIAuthError
    assert category_for_error(APIAuthError(401, "/x", "unauthorized")) == "auth_error"


def test_category_for_error_scaffold_simulated():
    from scaffold.mock_apis import SimulatedBadRequest, SimulatedTimeout, SimulatedAuthError
    assert category_for_error(SimulatedBadRequest("api_400")) == "client_error"
    assert category_for_error(SimulatedTimeout("timeout")) == "timeout"
    assert category_for_error(SimulatedAuthError("api_401_403")) == "auth_error"


def test_category_for_error_unknown():
    class WeirdError(Exception):
        pass
    assert category_for_error(WeirdError("weird")) == "unknown_error"