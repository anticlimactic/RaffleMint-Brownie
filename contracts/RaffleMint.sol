pragma solidity 0.8.11;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

contract RaffleMint is ERC721, Ownable {
    uint256 public constant MINT_VALUE = 0.08 * 1 ether; // immutable
    uint16 public constant MINT_SUPPLY = 5000; // immutable

    uint256 public deposit_start;
    uint256 public deposit_end;
    uint256 public mint_start;
    uint256 public mint_end;
    uint256 public withdraw_start;

    address[] public raffle;

    mapping (address => bool) raffleWinners;
    mapping (address => uint256) balances;

    // placeholder nonce
    uint256 start = 0;

    event Deposit(address addr, uint256 amount);
    event Withdraw(address addr, uint256 amount);
    event RaffleWinner(address addr);

    constructor(string memory _name, string memory _symbol) ERC721(_name, _symbol) {
        deposit_start = block.timestamp + 1 days;
        deposit_end = deposit_start + 1 weeks;
        mint_start = deposit_end + 3 days;
        mint_end = mint_start + 1 weeks;
        withdraw_start = deposit_end + 2 weeks;
    }

    function selectWinners() public onlyOwner {
        uint16 raffle_len = uint16(raffle.length);
        uint256 nonce = start;
        for (uint16 i = 0; i < MINT_SUPPLY; i++) {
            nonce = uint256(keccak256(abi.encodePacked(nonce)));
            uint256 rng = nonce % (raffle_len - i);
            address winner = raffle[rng];
            unchecked {
                balances[address(this)] += balances[winner];
            }
            balances[winner] = 0;
            raffleWinners[winner] = true;
            raffle[rng] = raffle[raffle_len - i - 1];
            raffle.pop();
            emit RaffleWinner(winner);
        }
    }

    receive() external payable {
        require(msg.value == MINT_VALUE, "incorrect amount");
        require(balances[msg.sender] == 0, "already deposited");
        balances[msg.sender] = msg.value;
        raffle.push(msg.sender);
        emit Deposit(msg.sender, msg.value);
    }

    function withdraw() public payable {
        require(block.timestamp > withdraw_start, "cannot withdraw yet");
        uint256 amount = balances[msg.sender];
        require(amount > 0, "no balance");
        balances[msg.sender] = 0;
        (bool success, ) = msg.sender.call{value: amount}("");
        require(success);
        emit Withdraw(msg.sender, amount);
    }

    function ownerWithdraw() public payable onlyOwner {
        require(block.timestamp > withdraw_start, "cannot withdraw yet");
        address mintAddress = address(this);
        uint256 amount = balances[mintAddress];
        require(amount > 0, "no balance");
        balances[mintAddress] = 0;
        (bool success, ) = msg.sender.call{value: amount}("");
        require(success);
        emit Withdraw(msg.sender, amount);
    }

    function ethBalanceOf(address addr) public view returns (uint256) {
        return balances[addr];
    }
}
