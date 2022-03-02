// SPDX-License-Identifier: MIT
pragma solidity 0.8.11;

import "@openzeppelin/contracts/utils/Counters.sol";
import "../RaffleMint.sol";

contract Test is RaffleMint {
    using Counters for Counters.Counter;

    Counters.Counter private _tokenIdCounter;

    uint16 public constant MAX_SUPPLY = 5;

    constructor(string memory _name, string memory _symbol)
        RaffleMint(_name, _symbol, MAX_SUPPLY)
    {}

    function mintRaffle() public {
        _tokenIdCounter.increment();
        _claimToken(msg.sender, _tokenIdCounter.current());
    }

    function totalSupply() external view returns (uint256) {
        return _tokenIdCounter.current();
    }
}
