import pytest


@pytest.fixture
def api():
    from rest_framework.test import APIClient

    return APIClient()
