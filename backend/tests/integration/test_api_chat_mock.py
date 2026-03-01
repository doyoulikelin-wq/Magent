import pytest

pytestmark = pytest.mark.skip(reason="requires dockerized postgres + redis stack")


def test_chat_mock_placeholder():
    assert True
