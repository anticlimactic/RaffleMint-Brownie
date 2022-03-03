import pytest

DECIMALS = 18
INITIAL_VALUE = "2000 ether"
DAY = 3600 * 24
WEEK = DAY * 7
ENTRY_COST = 80000000000000000  # 0.08 Ether


@pytest.fixture()
def gov(accounts):
    yield accounts[0]


@pytest.fixture()
def alice(accounts):
    yield accounts[1]


@pytest.fixture
def mint(Mint, gov):
    yield gov.deploy(Mint, "Test Token", "TEST")


@pytest.fixture
def raffle(Raffle, mock_vrf_coordinator, link_token, gov):
    yield gov.deploy(Raffle, mock_vrf_coordinator, link_token, 0, 10**17)


@pytest.fixture
def configured_raffle(Raffle, chain, mock_vrf_coordinator, link_token, gov):
    raffle_contract = gov.deploy(Raffle, mock_vrf_coordinator, link_token, 0, 10**17)

    chain_time = chain.time()

    total_winners = 5
    deposit_start = chain_time + DAY
    deposit_end = deposit_start + WEEK
    mint_start = deposit_end + 3 * DAY
    withdraw_start = mint_start + 1 * WEEK

    raffle_contract.configureRaffle(
        ENTRY_COST,
        total_winners,
        deposit_start,
        deposit_end,
        mint_start,
        withdraw_start,
        {"from": gov},
    )

    yield raffle_contract


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
