import brownie


def test_mint_deploy(mint):
    assert mint.address


def test_total_supply(mint):
    assert mint.totalSupply() == 0


def test_set_raffle_contract(mint, raffle, alice, gov):
    with brownie.reverts("Ownable: caller is not the owner"):
        mint.setRaffleContract(raffle.address, {"from": alice})

    mint.setRaffleContract(raffle.address, {"from": gov})

    assert mint.raffleContract() == raffle.address
