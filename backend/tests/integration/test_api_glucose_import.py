import pytest

pytestmark = pytest.mark.skip(reason="requires dockerized postgres + redis stack")


def test_glucose_import_flow_placeholder():
    assert True
