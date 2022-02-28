# RaffleMint

## Motivation

If a NFT project wishes to build a community, it must first start by having NFTs that are distributed within its community. This means nullifying the effects of bots and whales. Current solutions to this include whitelisting (labour intensive) and signatures (still certain issues and not decentralised).

Any economic incentive system must be designed such that it does not impact good users at all, or failing that, impacts good users the least. It must punish bad behaviour, ideally in proportion to the severity of the behaviour. With that in mind, `RaffleMint` uses the following strategy to attempt to discourage bad behaviour:

- Entries to the raffle are done once per address, and involve locking up ether for a period of time (>1 week)
- Raffle winners are chosen at random, using chainlink vrf as the nonce from which winners are drawn.
- After a certain amount of days after deposits end, withdrawals will be allowed by anyone who did not win a mint.

[Sybil attacks](https://en.wikipedia.org/wiki/Sybil_attack) are still possible, but the economic cost of doing so is high as the attacker must lock up an amount of ether equal to the amount of entries they submit. Users who only wish to flip NFTs will also be discouraged, as they may not wish to lock up their capital. Genuine users will likely not mind locking up their capital in exchange for a chance to join the community.
