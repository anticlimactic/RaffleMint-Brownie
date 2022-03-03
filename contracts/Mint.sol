// SPDX-License-Identifier: MIT
pragma solidity 0.8.11;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/utils/Counters.sol";

contract Mint is Ownable, ERC721 {
    using Counters for Counters.Counter;

    Counters.Counter private _tokenIdCounter;

    uint256 public constant MAX_SUPPLY = 5;

    address public raffleContract;

    constructor(string memory _name, string memory _symbol)
        ERC721(_name, _symbol)
    {}

    function mintRaffle(address _to) external {
        require(raffleContract == msg.sender, "caller is not raffle contract");

        uint256 tokenIndex = _tokenIdCounter.current() + 1;

        require(MAX_SUPPLY >= tokenIndex, "minted token exceeds supply");

        _tokenIdCounter.increment();
        _safeMint(_to, tokenIndex);
    }

    function totalSupply() external view returns (uint256) {
        return _tokenIdCounter.current();
    }

    function setRaffleContract(address _raffleContract) external onlyOwner {
        raffleContract = _raffleContract;
    }
}
