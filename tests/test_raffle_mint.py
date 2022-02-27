import pytest
import brownie

DAY = 3600 * 24
WEEK = DAY * 7

def test_deposit(raffle_mint, alice):
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


def test_withdraw_with_no_balance(raffle_mint, alice, chain):
    with brownie.reverts("cannot withdraw yet"):
        raffle_mint.withdraw({"from": alice})

    chain.sleep(4 * WEEK)

    with brownie.reverts("no balance"):
        raffle_mint.withdraw({"from": alice})


def test_withdraw_with_balance(raffle_mint, alice, chain):
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
