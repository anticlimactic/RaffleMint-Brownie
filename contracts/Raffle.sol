// SPDX-License-Identifier: MIT
pragma solidity 0.8.11;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@chainlink/contracts/src/v0.8/VRFConsumerBase.sol";

/// @title On-Chain Raffle Mechanism
/// @author @ItsCuzzo & @_anticlimactic

contract Raffle is Ownable, VRFConsumerBase {
    /// @dev Deprecates February 7, 2106 6:28:15 AM.
    struct RaffleConfig {
        uint64 entryCost;
        uint32 totalWinners;
        uint32 totalChosen;
        uint32 depositStart;
        uint32 depositEnd;
        uint32 mintStart;
        uint32 withdrawStart;
    }

    struct Entry {
        bool hasWon;
        uint248 amountDeposited;
    }

    RaffleConfig public raffle;

    mapping(address => Entry) public entries;

    /// @notice Token contract.
    address public tokenContract;

    /// @notice Array of entrants in the raffle.
    address[] public entrants;

    /// @notice Used to track the total amount of Ether that has been deposited by users.
    uint256 public totalDepositAmount;

    // Placeholder values.
    uint256 public nonceCache;
    bool public fetchedNonce;

    bytes32 private immutable _keyHash;
    uint256 private immutable _fee;

    event Deposit(address indexed addr, uint256 amount);
    event Withdraw(address indexed addr, uint256 amount);
    event Minted(address indexed addr);
    event RaffleWinner(address indexed addr);

    constructor(
        address _vrfCoordinator,
        address _link,
        bytes32 keyHash_,
        uint256 fee_
    ) VRFConsumerBase(_vrfCoordinator, _link) {
        _keyHash = keyHash_;
        _fee = fee_;
    }

    /// @notice Function used to configure the raffle.
    function configureRaffle(
        uint64 _entryCost,
        uint16 _totalWinners,
        uint32 _depositStart,
        uint32 _depositEnd,
        uint32 _mintStart,
        uint32 _withdrawStart
    ) public onlyOwner {
        require(
            _depositEnd > _depositStart,
            "deposit period cannot start after end"
        );
        require(
            _mintStart >= _depositEnd,
            "minting cannot begin before deposit ends"
        );
        require(
            _withdrawStart >= _mintStart + 1 weeks,
            "lockup period must exceed 1 week"
        );

        raffle.entryCost = _entryCost;
        raffle.depositStart = _depositStart;
        raffle.depositEnd = _depositEnd;
        raffle.mintStart = _mintStart;
        raffle.withdrawStart = _withdrawStart;
        raffle.totalWinners = _totalWinners;
    }

    /// @notice Function used to get a random number from VRF.
    function getRandomNumber() public onlyOwner returns (bytes32 requestId) {
        require(LINK.balanceOf(address(this)) >= _fee, "not enough LINK");
        return requestRandomness(_keyHash, _fee);
    }

    /// @notice Function used to uhhh... ???
    function fulfillRandomness(bytes32, uint256 randomness) internal override {
        nonceCache = randomness;
        fetchedNonce = true;
    }

    /// @notice Function used to fetch a nonce.
    function fetchNonce() external onlyOwner returns (bytes32) {
        require(
            block.timestamp >= raffle.depositEnd,
            "before deposit end time"
        );
        return getRandomNumber();
    }

    /// @notice Function used to select winners.
    /// @dev choose winner from raffle, remove winner from raffle, repeat
    function selectWinners(uint16 numWinners) public onlyOwner {
        require(
            block.timestamp >= raffle.depositEnd,
            "before deposit end time"
        );
        require(block.timestamp <= raffle.mintStart, "after mint start time");
        require(fetchedNonce, "vrf not called yet");
        require(
            raffle.totalChosen + numWinners <= raffle.totalWinners,
            "out of mints"
        );

        uint16 length = uint16(entrants.length);
        uint256 nonce = nonceCache;

        for (uint16 i = 0; i < numWinners; i++) {
            nonce = uint256(keccak256(abi.encodePacked(nonce)));

            uint256 rng = nonce % (length - i);
            address winner = entrants[rng];

            entries[winner].amountDeposited = 0;
            totalDepositAmount -= raffle.entryCost;

            entries[winner].hasWon = true;

            entrants[rng] = entrants[length - i - 1];
            entrants.pop();

            emit RaffleWinner(winner);
        }

        raffle.totalChosen += numWinners;
        nonceCache = nonce;
    }

    /// @notice Function used to enter the raffle.
    function enterRaffle() external payable {
        require(tx.origin == msg.sender, "contracts cannot enter");
        require(
            block.timestamp >= raffle.depositStart,
            "before deposit start time"
        );
        require(block.timestamp <= raffle.depositEnd, "after deposit end time");
        require(raffle.entryCost == msg.value, "incorrect Ether amount");
        require(entries[msg.sender].amountDeposited == 0, "already entered");

        totalDepositAmount += msg.value;
        entries[msg.sender].amountDeposited = uint248(msg.value);

        entrants.push(msg.sender);

        emit Deposit(msg.sender, msg.value);
    }

    /// @notice Function used by losing entrants to withdraw funds.
    function withdrawEntryCost() public payable {
        require(block.timestamp >= raffle.withdrawStart, "cannot withdraw yet");

        uint256 amount = entries[msg.sender].amountDeposited;

        require(amount > 0, "no balance");

        entries[msg.sender].amountDeposited = 0;
        (bool success, ) = msg.sender.call{value: amount}("");

        require(success, "withdraw failed");

        emit Withdraw(msg.sender, amount);
    }

    /// @notice Function used by the owner to withdraw raffle revenue.
    function withdrawOwnerFunds() public payable onlyOwner {
        require(block.timestamp >= raffle.withdrawStart, "cannot withdraw yet");

        uint256 ownerFunds = address(this).balance - totalDepositAmount;
        require(ownerFunds > 0, "no balance");

        (bool success, ) = msg.sender.call{value: ownerFunds}("");
        require(success, "withdraw failed");

        emit Withdraw(msg.sender, ownerFunds);
    }

    /// @notice Function used to claim a token from the minting contract.
    function claimToken() public {
        require(block.timestamp >= raffle.mintStart, "claiming is not active");
        require(entries[msg.sender].hasWon, "caller did not win");
        require(tokenContract != address(0), "address not set");

        // mintRaffle() selector.
        bytes memory payload = abi.encodeWithSignature(
            "mintRaffle(address)",
            msg.sender
        );
        (bool success, ) = tokenContract.call(payload);
        require(success, "claim failed");

        emit Minted(msg.sender);
    }

    /// @notice Function used to set the winning token address.
    function setTokenContract(address tokenContract_) public onlyOwner {
        tokenContract = tokenContract_;
    }
}
