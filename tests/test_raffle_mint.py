import brownie

DAY = 3600 * 24
WEEK = DAY * 7
MINT_PRICE = 80000000000000000  # 0.08 Ether


def test_deposit(configured_raffle, alice, chain):
    chain.sleep(DAY)
    chain.mine()
    with brownie.reverts("incorrect amount"):
        alice.transfer(configured_raffle.address, "1 ether")

    balance = alice.balance()
    tx = alice.transfer(configured_raffle.address, "0.08 ether")
    assert balance - "0.08 ether" == alice.balance()
    assert configured_raffle.ethBalanceOf(alice) == "0.08 ether"
    assert configured_raffle.balance() == "0.08 ether"
    event = tx.events["Deposit"]
    assert event["addr"] == alice.address
    assert event["amount"] == "0.08 ether"

    with brownie.reverts("already deposited"):
        alice.transfer(configured_raffle.address, "0.08 ether")


def test_deposit_timestamp(configured_raffle, alice, chain):
    with brownie.reverts("before deposit start time"):
        alice.transfer(configured_raffle.address, "0.8 ether")

    chain.sleep(WEEK + DAY)
    chain.mine()

    with brownie.reverts("after deposit end time"):
        alice.transfer(configured_raffle.address, "0.8 ether")


def test_withdraw_with_no_balance(configured_raffle, alice, chain):
    with brownie.reverts("cannot withdraw yet"):
        configured_raffle.withdraw({"from": alice})

    chain.sleep(4 * WEEK)
    chain.mine()

    with brownie.reverts("no balance"):
        configured_raffle.withdraw({"from": alice})


def test_withdraw_with_balance(configured_raffle, alice, chain):
    chain.sleep(DAY)
    chain.mine()
    alice.transfer(configured_raffle.address, "0.08 ether")

    chain.sleep(4 * WEEK)
    chain.mine()

    balance = alice.balance()
    tx = configured_raffle.withdraw({"from": alice})
    assert balance + "0.08 ether" == alice.balance()
    assert configured_raffle.ethBalanceOf(alice) == 0
    assert configured_raffle.balance() == "0 ether"
    event = tx.events["Withdraw"]
    assert event["addr"] == alice.address
    assert event["amount"] == "0.08 ether"


def test_owner_withdraw_with_no_balance(configured_raffle, gov, chain):
    with brownie.reverts("cannot withdraw yet"):
        configured_raffle.withdraw({"from": gov})

    chain.sleep(4 * WEEK)
    chain.mine()

    with brownie.reverts("no balance"):
        configured_raffle.withdraw({"from": gov})


def test_select_winners(
    configured_raffle, link_token, mock_vrf_coordinator, gov, accounts, chain
):
    link_token.transfer(configured_raffle.address, 10**18, {"from": gov})
    chain.sleep(DAY)
    chain.mine()
    accounts = accounts[1:10]  # remove gov from account list

    for account in accounts:
        account.transfer(configured_raffle.address, "0.08 ether")
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
    assert configured_raffle.ethBalanceOf(configured_raffle.address) == "0.08 ether"

    nonce = brownie.web3.toInt(brownie.web3.solidityKeccak(["uint256"], [nonce]))
    index = nonce % 9
    assert configured_raffle.ethBalanceOf(accounts[index]) == 0
    event = tx.events["RaffleWinner"]
    assert event["addr"] == accounts[index]
    accounts.pop(index)

    configured_raffle.selectWinners(4, {"from": gov})

    assert configured_raffle.balance() == "0.72 ether"
    assert configured_raffle.ethBalanceOf(configured_raffle.address) == "0.4 ether"

    for i in range(1, 4):
        nonce = brownie.web3.toInt(brownie.web3.solidityKeccak(["uint256"], [nonce]))
        index = nonce % (9 - i)
        assert configured_raffle.ethBalanceOf(accounts[index]) == 0
        accounts.pop(index)

    with brownie.reverts("out of mints"):
        configured_raffle.selectWinners(1, {"from": gov})
    with brownie.reverts("cannot withdraw yet"):
        configured_raffle.ownerWithdraw({"from": gov})

    chain.sleep(2 * WEEK)
    chain.mine()

    balance = gov.balance()
    configured_raffle.ownerWithdraw({"from": gov})
    assert balance + "0.4 ether" == gov.balance()

    with brownie.reverts("no balance"):
        configured_raffle.ownerWithdraw({"from": gov})


def test_select_winners_after_mint_start(configured_raffle, gov, accounts, chain):
    chain.sleep(DAY)
    chain.mine()
    for account in accounts[1:10]:
        account.transfer(configured_raffle.address, "0.08 ether")

    chain.sleep(WEEK * 2)
    chain.mine()

    with brownie.reverts("after mint start time"):
        configured_raffle.selectWinners(1, {"from": gov})


def test_claim_token(
    configured_raffle, link_token, mock_vrf_coordinator, accounts, gov, chain
):
    chain.sleep(DAY)
    chain.mine()

    for account in accounts[1:6]:
        account.transfer(configured_raffle.address, "0.08 ether")

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
        configured_raffle.mintRaffle({"from": accounts[7]})

    winner = accounts[1]
    configured_raffle.mintRaffle({"from": winner})

    assert configured_raffle.balanceOf(winner) == 1


def test_configure_raffle(test_contract, gov, chain):
    chain_time = chain.time()

    with brownie.reverts("deposit period cannot start after end"):
        test_contract.configureRaffle(
            MINT_PRICE,
            chain_time,
            chain_time - 1,
            chain_time + DAY,
            chain_time + WEEK,
            chain_time + WEEK,
            100,
            0
        )

    with brownie.reverts("mint period cannot start after end"):
        test_contract.configureRaffle(
            MINT_PRICE,
            chain_time,
            chain_time + 1,
            chain_time + DAY,
            chain_time + DAY - 1,
            chain_time + WEEK,
            100,
            0
        )

    with brownie.reverts("claim period must proceed mint period"):
        test_contract.configureRaffle(
            MINT_PRICE,
            chain_time,
            chain_time + 1,
            chain_time + DAY,
            chain_time + DAY + 1,
            chain_time + DAY - 1,
            100,
            0
        )

    depositEnd = chain_time + 1
    mintStart = chain_time + DAY
    mintEnd = chain_time + DAY + 1
    withdrawStart = chain_time + DAY + 2
    mintSupply = 100
    minted = 0

    test_contract.configureRaffle(
        MINT_PRICE,
        chain_time,
        depositEnd,
        mintStart,
        mintEnd,
        withdrawStart,
        mintSupply,
        minted
    )

    raffle = test_contract.raffleConfig()
    
    assert MINT_PRICE == raffle['mintValue']
    assert chain_time == raffle['depositStart']
    assert depositEnd == raffle['depositEnd']
    assert mintStart == raffle['mintStart']
    assert mintEnd == raffle['mintEnd']
    assert withdrawStart == raffle['withdrawStart']
    assert mintSupply == raffle['mintSupply']
    assert minted == raffle['minted']
