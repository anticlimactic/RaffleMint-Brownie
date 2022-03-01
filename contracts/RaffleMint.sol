// SPDX-License-Identifier: MIT
pragma solidity 0.8.11;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@chainlink/contracts/src/v0.8/interfaces/LinkTokenInterface.sol";
import "@chainlink/contracts/src/v0.8/interfaces/VRFCoordinatorV2Interface.sol";
import "@chainlink/contracts/src/v0.8/VRFConsumerBase.sol";

/// @title ERC721 with Raffle
contract RaffleMint is ERC721, VRFConsumerBase, Ownable {
    /// @notice mint cost per NFT
    uint256 public constant MINT_VALUE = 0.08 * 1 ether; // immutable
    /// @notice total raffle mint supply
    uint16 public mintSupply;
    /// @notice minted raffle mint count
    uint16 public minted;

    /// @notice deposit ether start time
    uint256 public depositStart;
    /// @notice deposit ether end time
    uint256 public depositEnd;
    /// @notice raffle mint start time
    uint256 public mintStart;
    /// @notice raffle mint end time
    uint256 public mintEnd;
    /// @notice withdraw ether start time
    uint256 public withdrawStart;

    /// @notice winners chosen from array of raffle participants
    address[] public raffle;

    /// @notice whether participant won or not
    mapping(address => bool) public raffleWinners;
    /// @notice ether owed balances
    mapping(address => uint256) public balances;

    // placeholder nonce
    uint256 public nonceCache = 0;
    bool public fetchedNonce = false;
    address constant vrfCoordinator = 0x271682DEB8C4E0901D1a1550aD2e64D568E69909;
    address constant link = 0x514910771AF9Ca656af840dff83E8264EcF986CA;
    bytes32 constant keyHash = 0x8af398995b04c28e9951adb9721ef74c74f93e6a478f39e7e0777be13527e7ef;
    uint256 constant fee = 0.25 * 10 ** 18;

    event Deposit(address addr, uint256 amount);
    event Withdraw(address addr, uint256 amount);
    event Minted(address addr, uint256 tokenId);
    event RaffleWinner(address addr);

    constructor(
        string memory _name,
        string memory _symbol,
        uint16 _supply
    ) ERC721(_name, _symbol) VRFConsumerBase(vrfCoordinator, link) {
        depositStart = block.timestamp + 1 days;
        depositEnd = depositStart + 1 weeks;
        mintStart = depositEnd + 3 days;
        mintEnd = mintStart + 1 weeks;
        withdrawStart = depositEnd + 2 weeks;
        mintSupply = _supply;
    }

   function getRandomNumber() public returns (bytes32 requestId) {
        require(LINK.balanceOf(address(this)) >= fee, "not enough LINK");
        return requestRandomness(keyHash, fee);
    }

    function fulfillRandomness(bytes32 requestId, uint256 randomness) internal override {
        nonceCache = randomness;
        fetchedNonce = true;
    }

    function fetchNonce() external onlyOwner {
        getRandomNumber();
    }

    /// @notice select winners
    /// @dev choose winner from raffle, remove winner from raffle, repeat
    function selectWinners(uint16 amount) public onlyOwner {
        require(fetchedNonce, "vrf not called yet");
        require(block.timestamp >= depositEnd, "before deposit end time");
        require(block.timestamp < mintStart, "after mint start time");
        require(minted + amount <= mintSupply, "out of mints");
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
        require(block.timestamp >= depositStart, "before deposit start time");
        require(block.timestamp < depositEnd, "after deposit end time");
        require(msg.value == MINT_VALUE, "incorrect amount");
        require(balances[msg.sender] == 0, "already deposited");
        balances[msg.sender] = msg.value;
        raffle.push(msg.sender);
        emit Deposit(msg.sender, msg.value);
    }

    /// @notice withdraw ether from raffle
    function withdraw() public payable {
        require(block.timestamp > withdrawStart, "cannot withdraw yet");
        uint256 amount = balances[msg.sender];
        require(amount > 0, "no balance");
        balances[msg.sender] = 0;
        (bool success, ) = msg.sender.call{value: amount}("");
        require(success, "withdraw failed");
        emit Withdraw(msg.sender, amount);
    }

    /// @notice owner withdraws ether from raffle
    function ownerWithdraw() public payable onlyOwner {
        require(block.timestamp > withdrawStart, "cannot withdraw yet");
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
            block.timestamp >= mintStart && mintEnd >= block.timestamp,
            "claiming is not active"
        );

        _safeMint(_to, _tokenId);

        emit Minted(_to, _tokenId);
    }
}
