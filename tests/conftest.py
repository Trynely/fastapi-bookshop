import pytest
from faker import Faker

@pytest.fixture
def faker_() -> Faker:
    return Faker()