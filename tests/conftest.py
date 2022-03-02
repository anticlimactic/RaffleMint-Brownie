import pytest

DECIMALS = 18
INITIAL_VALUE = "2000 ether"


@pytest.fixture()
def gov(accounts):
    yield accounts[0]


@pytest.fixture()
def alice(accounts):
    yield accounts[1]


@pytest.fixture()
def raffle_mint(RaffleMint, link_token, mock_vrf_coordinator, gov):
    yield gov.deploy(
        RaffleMint, "name", "symbol", 5, 0, mock_vrf_coordinator, link_token, 10**17
    )


@pytest.fixture
def test_contract(Test, link_token, mock_vrf_coordinator, gov):
    yield gov.deploy(
        Test, "Test", "TEST", 0, mock_vrf_coordinator, link_token, 10**17
    )


@pytest.fixture
def link_token(LinkToken, gov):
    yield LinkToken.deploy({"from": gov})


@pytest.fixture()
def mock_price_feed(MockV3Aggregator, gov):
    yield MockV3Aggregator.deploy(DECIMALS, INITIAL_VALUE, {"from": gov})


@pytest.fixture()
def mock_vrf_coordinator(VRFCoordinatorMock, gov, link_token):
    yield VRFCoordinatorMock.deploy(link_token.address, {"from": gov})


@pytest.fixture
def mock_oracle(MockOracle, gov, link_token):
    yield MockOracle.deploy(link_token.address, {"from": gov})


@pytest.fixture(scope="module", autouse=True)
def shared_setup(module_isolation):
    pass
