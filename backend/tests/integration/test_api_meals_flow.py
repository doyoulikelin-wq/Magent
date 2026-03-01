import pytest

pytestmark = pytest.mark.skip(reason="requires dockerized postgres + redis stack")


def test_meals_photo_flow_placeholder():
    assert True
