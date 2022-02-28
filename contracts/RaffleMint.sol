pragma solidity 0.8.11;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

/// @title ERC721 with Raffle
contract RaffleMint is ERC721, Ownable {
    /// @notice mint cost per NFT
    uint256 public constant MINT_VALUE = 0.08 * 1 ether; // immutable
    /// @notice raffle mint supply
    uint16 public constant MINT_SUPPLY = 5000; // immutable

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
    uint256 public start = 0;

    event Deposit(address addr, uint256 amount);
    event Withdraw(address addr, uint256 amount);
    event RaffleWinner(address addr);

    constructor(string memory _name, string memory _symbol)
        ERC721(_name, _symbol)
    {
        depositStart = block.timestamp + 1 days;
        depositEnd = depositStart + 1 weeks;
        mintStart = depositEnd + 3 days;
        mintEnd = mintStart + 1 weeks;
        withdrawStart = depositEnd + 2 weeks;
    }

    /// @notice select winners
    /// @dev choose winner from raffle, remove winner from raffle, repeat
    function selectWinners() public onlyOwner {
        uint16 length = uint16(raffle.length);
        uint256 nonce = start;
        for (uint16 i = 0; i < MINT_SUPPLY; i++) {
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
}
