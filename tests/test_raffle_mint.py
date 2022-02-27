import brownie

DAY = 3600 * 24
WEEK = DAY * 7


def test_deposit(raffle_mint, alice, chain):
    chain.sleep(DAY)
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

    with brownie.reverts("after deposit end time"):
        alice.transfer(raffle_mint.address, "0.8 ether")


def test_withdraw_with_no_balance(raffle_mint, alice, chain):
    with brownie.reverts("cannot withdraw yet"):
        raffle_mint.withdraw({"from": alice})

    chain.sleep(4 * WEEK)

    with brownie.reverts("no balance"):
        raffle_mint.withdraw({"from": alice})


def test_withdraw_with_balance(raffle_mint, alice, chain):
    chain.sleep(DAY)
    alice.transfer(raffle_mint.address, "0.08 ether")

    chain.sleep(4 * WEEK)

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

    with brownie.reverts("no balance"):
        raffle_mint.withdraw({"from": gov})


def test_owner_withdraw_with_balance(raffle_mint, gov, chain):
    pass
