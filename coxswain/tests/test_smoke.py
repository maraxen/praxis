import coxswain


def test_version_is_a_string() -> None:
    assert isinstance(coxswain.__version__, str)
