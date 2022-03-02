import brownie

DAY = 3600 * 24
WEEK = DAY * 7


def test_deposit(raffle_mint, alice, chain):
    chain.sleep(DAY)
    chain.mine()
    with brownie.reverts("incorrect amount"):
        alice.transfer(raffle_mint.address, "1 ether")

    balance = alice.balance()
    tx = alice.transfer(raffle_mint.address, "0.08 ether")
    assert balance - "0.08 ether" == alice.balance()
    assert raffle_mint.ethBalanceOf(alice) == "0.08 ether"
    assert raffle_mint.balance() == "0.08 ether"
    event = tx.events["Deposit"]
    assert event["addr"] == alice.address
    assert event["amount"] == "0.08 ether"

    with brownie.reverts("already deposited"):
        alice.transfer(raffle_mint.address, "0.08 ether")


def test_deposit_timestamp(raffle_mint, alice, chain):
    with brownie.reverts("before deposit start time"):
        alice.transfer(raffle_mint.address, "0.8 ether")

    chain.sleep(WEEK + DAY)
    chain.mine()

    with brownie.reverts("after deposit end time"):
        alice.transfer(raffle_mint.address, "0.8 ether")


def test_withdraw_with_no_balance(raffle_mint, alice, chain):
    with brownie.reverts("cannot withdraw yet"):
        raffle_mint.withdraw({"from": alice})

    chain.sleep(4 * WEEK)
    chain.mine()

    with brownie.reverts("no balance"):
        raffle_mint.withdraw({"from": alice})


def test_withdraw_with_balance(raffle_mint, alice, chain):
    chain.sleep(DAY)
    chain.mine()
    alice.transfer(raffle_mint.address, "0.08 ether")

    chain.sleep(4 * WEEK)
    chain.mine()

    balance = alice.balance()
    tx = raffle_mint.withdraw({"from": alice})
    assert balance + "0.08 ether" == alice.balance()
    assert raffle_mint.ethBalanceOf(alice) == 0
    assert raffle_mint.balance() == "0 ether"
    event = tx.events["Withdraw"]
    assert event["addr"] == alice.address
    assert event["amount"] == "0.08 ether"


def test_owner_withdraw_with_no_balance(raffle_mint, gov, chain):
    with brownie.reverts("cannot withdraw yet"):
        raffle_mint.withdraw({"from": gov})

    chain.sleep(4 * WEEK)
    chain.mine()

    with brownie.reverts("no balance"):
        raffle_mint.withdraw({"from": gov})


def test_select_winners(
    raffle_mint, link_token, mock_vrf_coordinator, gov, accounts, chain
):
    link_token.transfer(raffle_mint.address, 10**18, {"from": gov})
    chain.sleep(DAY)
    chain.mine()
    accounts = accounts[1:10]  # remove gov from account list

    for account in accounts:
        account.transfer(raffle_mint.address, "0.08 ether")
    with brownie.reverts("vrf not called yet"):
        raffle_mint.selectWinners(1, {"from": gov})

    tx_receipt = raffle_mint.fetchNonce({"from": gov})
    request_id = tx_receipt.return_value
    assert isinstance(tx_receipt.txid, str)

    mock_vrf_coordinator.callBackWithRandomness(
        request_id, 777, raffle_mint.address, {"from": gov}
    )
    assert raffle_mint.nonceCache() > 0
    nonce = raffle_mint.nonceCache()

    with brownie.reverts("before deposit end time"):
        raffle_mint.selectWinners(1, {"from": gov})

    chain.sleep(WEEK)
    chain.mine()
    with brownie.reverts("out of mints"):
        raffle_mint.selectWinners(10, {"from": gov})

    tx = raffle_mint.selectWinners(1, {"from": gov})
    assert raffle_mint.ethBalanceOf(raffle_mint.address) == "0.08 ether"

    nonce = brownie.web3.toInt(brownie.web3.solidityKeccak(["uint256"], [nonce]))
    index = nonce % 9
    assert raffle_mint.ethBalanceOf(accounts[index]) == 0
    event = tx.events["RaffleWinner"]
    assert event["addr"] == accounts[index]
    accounts.pop(index)

    raffle_mint.selectWinners(4, {"from": gov})

    assert raffle_mint.balance() == "0.72 ether"
    assert raffle_mint.ethBalanceOf(raffle_mint.address) == "0.4 ether"

    for i in range(1, 4):
        nonce = brownie.web3.toInt(brownie.web3.solidityKeccak(["uint256"], [nonce]))
        index = nonce % (9 - i)
        assert raffle_mint.ethBalanceOf(accounts[index]) == 0
        accounts.pop(index)

    with brownie.reverts("out of mints"):
        raffle_mint.selectWinners(1, {"from": gov})
    with brownie.reverts("cannot withdraw yet"):
        raffle_mint.ownerWithdraw({"from": gov})

    chain.sleep(2 * WEEK)
    chain.mine()

    balance = gov.balance()
    raffle_mint.ownerWithdraw({"from": gov})
    assert balance + "0.4 ether" == gov.balance()

    with brownie.reverts("no balance"):
        raffle_mint.ownerWithdraw({"from": gov})


def test_select_winners_after_mint_start(
    raffle_mint, link_token, mock_vrf_coordinator, gov, accounts, chain
):
    chain.sleep(DAY)
    chain.mine()
    for account in accounts[1:10]:
        account.transfer(raffle_mint.address, "0.08 ether")

    chain.sleep(WEEK * 2)
    chain.mine()

    link_token.transfer(raffle_mint.address, 10**18, {"from": gov})
    tx_receipt = raffle_mint.fetchNonce({"from": gov})
    request_id = tx_receipt.return_value
    assert isinstance(tx_receipt.txid, str)

    mock_vrf_coordinator.callBackWithRandomness(
        request_id, 777, raffle_mint.address, {"from": gov}
    )

    with brownie.reverts("after mint start time"):
        raffle_mint.selectWinners(1, {"from": gov})


def test_claim_token(test_contract, accounts, gov, chain):
    chain.sleep(DAY)

    for account in accounts[1:6]:
        account.transfer(test_contract.address, "0.08 ether")

    assert test_contract.balance() == "0.40 ether"

    chain.sleep(WEEK)

    with brownie.reverts("out of mints"):
        test_contract.selectWinners(6, {"from": gov})

    test_contract.selectWinners(3, {"from": gov})

    chain.sleep(3 * DAY)

    with brownie.reverts("caller did not win"):
        test_contract.mintRaffle({"from": accounts[7]})

    winner = accounts[1]
    test_contract.mintRaffle({"from": winner})

    assert test_contract.balanceOf(winner) == 1
