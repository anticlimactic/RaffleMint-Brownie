// SPDX-License-Identifier: MIT
pragma solidity 0.8.11;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@chainlink/contracts/src/v0.8/VRFConsumerBase.sol";

/// @title ERC721 with Raffle
contract RaffleMint is ERC721, VRFConsumerBase, Ownable {
    /// @notice mint cost per NFT
    uint256 public constant MINT_VALUE = 0.08 ether; // immutable

    /// @notice minted raffle mint count
    uint16 public minted;

    /// @notice Struct used for configuring raffle
    struct Raffle {
        uint64 mintValue;
        uint32 depositStart;
        uint32 depositEnd;
        uint32 mintStart;
        uint32 mintEnd;
        uint32 withdrawStart;
        uint16 mintSupply;
        uint16 minted;
    }

    Raffle public raffleConfig;

    /// @notice winners chosen from array of raffle participants
    address[] public raffle;

    /// @notice whether participant won or not
    mapping(address => bool) public raffleWinners;
    /// @notice ether owed balances
    mapping(address => uint256) public balances;

    // placeholder nonce
    uint256 public nonceCache = 0;
    bool public fetchedNonce = false;
    bytes32 public keyhash; // immutable;
    uint256 public fee; // immutable;

    event Deposit(address addr, uint256 amount);
    event Withdraw(address addr, uint256 amount);
    event Minted(address addr, uint256 tokenId);
    event RaffleWinner(address addr);

    constructor(
        string memory _name,
        string memory _symbol,
        uint16 _supply,
        bytes32 _keyhash,
        address _vrfCoordinator,
        address _link,
        uint256 _fee
    ) ERC721(_name, _symbol) VRFConsumerBase(_vrfCoordinator, _link) {
        raffleConfig.mintSupply = _supply;
        keyhash = _keyhash;
        fee = _fee;
    }

    /// @notice Function used to configure a raffle
    function configureRaffle(
        uint64 _mintValue,
        uint32 _depositStart,
        uint32 _depositEnd,
        uint32 _mintStart,
        uint32 _mintEnd,
        uint32 _withdrawStart,
        uint16 _mintSupply,
        uint16 _minted
    ) public onlyOwner {
        require(
            _depositEnd > _depositStart,
            "deposit period cannot start after end"
        );
        require(_mintEnd > _mintStart, "mint period cannot start after end");
        require(
            _withdrawStart > _mintEnd,
            "claim period must proceed mint period"
        );

        raffleConfig.mintValue = _mintValue;
        raffleConfig.depositStart = _depositStart;
        raffleConfig.depositEnd = _depositEnd;
        raffleConfig.mintStart = _mintStart;
        raffleConfig.mintEnd = _mintEnd;
        raffleConfig.withdrawStart = _withdrawStart;
        raffleConfig.mintSupply = _mintSupply;
        raffleConfig.minted = _minted;
    }

    function getRandomNumber() public onlyOwner returns (bytes32 requestId) {
        require(LINK.balanceOf(address(this)) >= fee, "not enough LINK");
        return requestRandomness(keyhash, fee);
    }

    function fulfillRandomness(bytes32 requestId, uint256 randomness)
        internal
        override
    {
        nonceCache = randomness;
        fetchedNonce = true;
    }

    function fetchNonce() external onlyOwner returns (bytes32) {
        require(
            block.timestamp >= raffleConfig.depositEnd,
            "before deposit end time"
        );
        return getRandomNumber();
    }

    /// @notice select winners
    /// @dev choose winner from raffle, remove winner from raffle, repeat
    function selectWinners(uint16 amount) public onlyOwner {
        require(
            block.timestamp >= raffleConfig.depositEnd,
            "before deposit end time"
        );
        require(
            block.timestamp < raffleConfig.mintStart,
            "after mint start time"
        );
        require(fetchedNonce, "vrf not called yet");
        require(minted + amount <= raffleConfig.mintSupply, "out of mints");
        uint16 length = uint16(raffle.length);
        uint256 nonce = nonceCache;
        for (uint16 i = 0; i < amount; i++) {
            nonce = uint256(keccak256(abi.encodePacked(nonce)));
            uint256 rng = nonce % (length - i);
            address winner = raffle[rng];
            unchecked {
                balances[address(this)] += balances[winner];
            }
            balances[winner] = 0;
            raffleWinners[winner] = true;
            raffle[rng] = raffle[length - i - 1];
            raffle.pop();
            emit RaffleWinner(winner);
        }
        minted = minted + amount;
        nonceCache = nonce;
    }

    /// @notice receive ether from raffle participants
    receive() external payable {
        require(
            block.timestamp >= raffleConfig.depositStart,
            "before deposit start time"
        );
        require(
            block.timestamp < raffleConfig.depositEnd,
            "after deposit end time"
        );
        require(msg.value == MINT_VALUE, "incorrect amount");
        require(balances[msg.sender] == 0, "already deposited");
        balances[msg.sender] = msg.value;
        raffle.push(msg.sender);
        emit Deposit(msg.sender, msg.value);
    }

    /// @notice withdraw ether from raffle
    function withdraw() public payable {
        require(
            block.timestamp > raffleConfig.withdrawStart,
            "cannot withdraw yet"
        );
        uint256 amount = balances[msg.sender];
        require(amount > 0, "no balance");
        balances[msg.sender] = 0;
        (bool success, ) = msg.sender.call{value: amount}("");
        require(success, "withdraw failed");
        emit Withdraw(msg.sender, amount);
    }

    /// @notice owner withdraws ether from raffle
    function ownerWithdraw() public payable onlyOwner {
        require(
            block.timestamp > raffleConfig.withdrawStart,
            "cannot withdraw yet"
        );
        address mintAddress = address(this);
        uint256 amount = balances[mintAddress];
        require(amount > 0, "no balance");
        balances[mintAddress] = 0;
        (bool success, ) = msg.sender.call{value: amount}("");
        require(success, "withdraw failed");
        emit Withdraw(msg.sender, amount);
    }

    function ethBalanceOf(address addr) public view returns (uint256) {
        return balances[addr];
    }

    /// @notice Function used to mint a token to a raffle winner.
    /// @param _to The receiving token address.
    /// @param _tokenId The token ID to be minted to `_to`.
    /// @dev This function would be called in an implementation of
    /// the inheriting contract.
    function _claimToken(address _to, uint256 _tokenId) internal {
        require(raffleWinners[_to], "caller did not win");
        require(
            block.timestamp >= raffleConfig.mintStart &&
                raffleConfig.mintEnd >= block.timestamp,
            "claiming is not active"
        );

        _safeMint(_to, _tokenId);

        emit Minted(_to, _tokenId);
    }
}
