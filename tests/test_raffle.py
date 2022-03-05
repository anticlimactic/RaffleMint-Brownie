import brownie

DAY = 3600 * 24
WEEK = DAY * 7


def test_raffle_deploy(raffle):
    assert raffle.address


def test_configure_raffle(raffle, mint, chain, alice, gov):

    raffle.setTokenContract(mint.address, {"from": gov})

    entry_cost = 80000000000000000  # 0.08 Ether
    deposit_start = chain.time()
    total_winners = 5
    deposit_end = deposit_start + WEEK
    mint_start = deposit_end + 3 * DAY
    withdraw_start = deposit_end + 2 * WEEK

    with brownie.reverts("Ownable: caller is not the owner"):
        raffle.configureRaffle(
            entry_cost,
            total_winners,
            deposit_start,
            deposit_end,
            mint_start,
            withdraw_start,
            {"from": alice},
        )

    with brownie.reverts("deposit period cannot start after end"):
        raffle.configureRaffle(
            entry_cost,
            total_winners,
            deposit_start,
            deposit_start - 1,
            mint_start,
            withdraw_start,
            {"from": gov},
        )

    with brownie.reverts("minting cannot begin before deposit ends"):
        raffle.configureRaffle(
            entry_cost,
            total_winners,
            deposit_start,
            deposit_end,
            deposit_end - 1,
            withdraw_start,
            {"from": gov},
        )

    with brownie.reverts("lockup period must exceed 1 week"):
        raffle.configureRaffle(
            entry_cost,
            total_winners,
            deposit_start,
            deposit_end,
            mint_start,
            mint_start,
            {"from": gov},
        )

    raffle.configureRaffle(
        entry_cost,
        total_winners,
        deposit_start,
        deposit_end,
        mint_start,
        withdraw_start,
        {"from": gov},
    )

    raffleConfig = raffle.raffle()

    assert entry_cost == raffleConfig["entryCost"]
    assert total_winners == raffleConfig["totalWinners"]
    assert deposit_start == raffleConfig["depositStart"]
    assert deposit_end == raffleConfig["depositEnd"]
    assert mint_start == raffleConfig["mintStart"]
    assert withdraw_start == raffleConfig["withdrawStart"]


def test_enter_raffle(configured_raffle, alice, chain):
    chain.sleep(DAY)
    chain.mine()

    with brownie.reverts("incorrect Ether amount"):
        configured_raffle.enterRaffle({"from": alice, "value": "0.07 ether"})

    balance = alice.balance()
    tx = configured_raffle.enterRaffle({"from": alice, "value": "0.08 ether"})

    assert balance - "0.08 ether" == alice.balance()
    assert configured_raffle.entries(alice.address)["amountDeposited"] == "0.08 ether"
    assert configured_raffle.balance() == "0.08 ether"

    event = tx.events["Deposit"]

    assert event["addr"] == alice.address
    assert event["amount"] == "0.08 ether"

    with brownie.reverts("already entered"):
        configured_raffle.enterRaffle({"from": alice, "value": "0.08 ether"})


def test_enter_raffle_timestamps(configured_raffle, alice, chain):
    with brownie.reverts("before deposit start time"):
        configured_raffle.enterRaffle({"from": alice, "value": "0.08 ether"})

    chain.sleep(2 * WEEK)
    chain.mine()

    with brownie.reverts("after deposit end time"):
        configured_raffle.enterRaffle({"from": alice, "value": "0.08 ether"})


def test_withdraw_entry_cost_with_no_balance(configured_raffle, alice, chain):
    with brownie.reverts("cannot withdraw yet"):
        configured_raffle.withdrawEntryCost({"from": alice})

    chain.sleep(4 * WEEK)
    chain.mine()

    with brownie.reverts("no balance"):
        configured_raffle.withdrawEntryCost({"from": alice})


def test_withdraw_entry_cost_with_balance(configured_raffle, alice, chain):
    chain.sleep(DAY)
    chain.mine()

    configured_raffle.enterRaffle({"from": alice, "value": "0.08 ether"})

    chain.sleep(4 * WEEK)
    chain.mine()

    balance = alice.balance()

    tx = configured_raffle.withdrawEntryCost({"from": alice})

    assert balance + "0.08 ether" == alice.balance()
    assert configured_raffle.entries(alice.address)["amountDeposited"] == 0
    assert configured_raffle.balance() == "0 ether"

    event = tx.events["Withdraw"]

    assert event["addr"] == alice.address
    assert event["amount"] == "0.08 ether"


def test_withdraw_owner_funds_with_no_balance(configured_raffle, gov, chain):
    with brownie.reverts("cannot withdraw yet"):
        configured_raffle.withdrawOwnerFunds({"from": gov})

    chain.sleep(4 * WEEK)
    chain.mine()

    with brownie.reverts("no balance"):
        configured_raffle.withdrawOwnerFunds({"from": gov})


def test_select_winners(
    configured_raffle, link_token, mock_vrf_coordinator, gov, accounts, chain
):
    link_token.transfer(configured_raffle.address, 10**18, {"from": gov})

    chain.sleep(DAY)
    chain.mine()

    accounts = accounts[1:10]  # remove gov from account list

    for account in accounts:
        configured_raffle.enterRaffle({"from": account, "value": "0.08 ether"})

    with brownie.reverts("before deposit end time"):
        configured_raffle.fetchNonce({"from": gov})

    with brownie.reverts("before deposit end time"):
        configured_raffle.selectWinners(1, {"from": gov})

    chain.sleep(WEEK)
    chain.mine()

    with brownie.reverts("vrf not called yet"):
        configured_raffle.selectWinners(1, {"from": gov})

    tx_receipt = configured_raffle.fetchNonce({"from": gov})
    request_id = tx_receipt.return_value
    assert isinstance(tx_receipt.txid, str)

    mock_vrf_coordinator.callBackWithRandomness(
        request_id, 777, configured_raffle.address, {"from": gov}
    )

    assert configured_raffle.nonceCache() > 0
    nonce = configured_raffle.nonceCache()

    with brownie.reverts("out of mints"):
        configured_raffle.selectWinners(10, {"from": gov})

    tx = configured_raffle.selectWinners(1, {"from": gov})

    nonce = brownie.web3.toInt(brownie.web3.solidityKeccak(["uint256"], [nonce]))
    index = nonce % 9

    event = tx.events["RaffleWinner"]

    assert event["addr"] == accounts[index]
    accounts.pop(index)

    configured_raffle.selectWinners(4, {"from": gov})

    for i in range(1, 4):
        nonce = brownie.web3.toInt(brownie.web3.solidityKeccak(["uint256"], [nonce]))
        index = nonce % (9 - i)
        assert configured_raffle.entries(accounts[index])["hasWon"] == True

    assert configured_raffle.balance() == "0.72 ether"

    with brownie.reverts("out of mints"):
        configured_raffle.selectWinners(1, {"from": gov})

    with brownie.reverts("cannot withdraw yet"):
        configured_raffle.withdrawOwnerFunds({"from": gov})

    chain.sleep(4 * WEEK)
    chain.mine()


def test_select_winners_after_mint_start(configured_raffle, gov, accounts, chain):
    chain.sleep(DAY)
    chain.mine()

    for account in accounts[1:10]:
        configured_raffle.enterRaffle({"from": account, "value": "0.08 ether"})

    chain.sleep(2 * WEEK)
    chain.mine()

    with brownie.reverts("after mint start time"):
        configured_raffle.selectWinners(1, {"from": gov})


def test_claim_token(
    configured_raffle, mint, link_token, mock_vrf_coordinator, accounts, gov, chain
):
    mint.setRaffleContract(configured_raffle.address, {"from": gov})

    chain.sleep(DAY)
    chain.mine()

    for account in accounts[1:6]:
        configured_raffle.enterRaffle({"from": account, "value": "0.08 ether"})

    assert configured_raffle.balance() == "0.40 ether"

    chain.sleep(WEEK)
    chain.mine()

    link_token.transfer(configured_raffle.address, 10**18, {"from": gov})
    tx_receipt = configured_raffle.fetchNonce({"from": gov})
    request_id = tx_receipt.return_value
    mock_vrf_coordinator.callBackWithRandomness(
        request_id, 777, configured_raffle.address, {"from": gov}
    )

    with brownie.reverts("out of mints"):
        configured_raffle.selectWinners(6, {"from": gov})

    configured_raffle.selectWinners(3, {"from": gov})

    chain.sleep(3 * DAY)
    chain.mine()

    with brownie.reverts("caller did not win"):
        configured_raffle.claimToken({"from": accounts[7]})

    winner = accounts[1]
    configured_raffle.claimToken({"from": winner})

    assert mint.balanceOf(winner) == 1

    balance = gov.balance()

    chain.sleep(WEEK)
    chain.mine()

    configured_raffle.withdrawOwnerFunds({"from": gov})
    assert balance + "0.08 ether" == gov.balance()

    entry = configured_raffle.entries(winner.address)
    assert entry["hasWon"] == True
    assert entry["amountDeposited"] == 0


def test_claim_token_reverts(
    configured_raffle, mint, link_token, mock_vrf_coordinator, alice, gov, chain
):
    with brownie.reverts("claiming is not active"):
        configured_raffle.claimToken({"from": alice})

    chain.sleep(DAY)
    chain.mine()

    configured_raffle.enterRaffle({"from": alice, "value": "0.08 ether"})

    chain.sleep(WEEK)
    chain.mine()

    link_token.transfer(configured_raffle.address, 10**18, {"from": gov})
    tx_receipt = configured_raffle.fetchNonce({"from": gov})
    request_id = tx_receipt.return_value
    mock_vrf_coordinator.callBackWithRandomness(
        request_id, 777, configured_raffle.address, {"from": gov}
    )

    configured_raffle.selectWinners(1, {"from": gov})

    chain.sleep(3 * DAY)
    chain.mine()

    assert configured_raffle.entries(alice.address)["hasWon"]

    mint.setRaffleContract(configured_raffle.address, {"from": gov})
    configured_raffle.claimToken({"from": alice})

    assert mint.balanceOf(alice) == 1


def test_locked_contract_state(raffle, mint, chain, gov):
    entry_cost = 80000000000000000  # 0.08 Ether
    deposit_start = chain.time()
    total_winners = 5
    deposit_end = deposit_start + WEEK
    mint_start = deposit_end + 3 * DAY
    withdraw_start = deposit_end + 2 * WEEK

    with brownie.reverts("token contract not set"):
        raffle.configureRaffle(
            entry_cost,
            total_winners,
            deposit_start,
            deposit_end,
            mint_start,
            withdraw_start,
            {"from": gov},
        )

    raffle.setTokenContract(mint.address, {"from": gov})

    raffle.configureRaffle(
        entry_cost,
        total_winners,
        deposit_start,
        deposit_end,
        mint_start,
        withdraw_start,
        {"from": gov},
    )

    with brownie.reverts("contract is locked"):
        raffle.configureRaffle(
            entry_cost,
            total_winners,
            deposit_start,
            deposit_end,
            mint_start,
            withdraw_start,
            {"from": gov},
        )

    with brownie.reverts("contract is locked"):
        raffle.setTokenContract(mint.address, {"from": gov})
