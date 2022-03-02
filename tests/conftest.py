import pytest


@pytest.fixture()
def gov(accounts):
    yield accounts[0]


@pytest.fixture()
def alice(accounts):
    yield accounts[1]


@pytest.fixture
def raffle_mint(RaffleMint, gov):
    yield gov.deploy(RaffleMint, "name", "symbol", 5)


@pytest.fixture
def test_contract(Test, gov):
    yield gov.deploy(Test, "Test", "TEST")
