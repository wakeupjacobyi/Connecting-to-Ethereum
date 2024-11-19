// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";

contract Source is AccessControl {
    bytes32 public constant ADMIN_ROLE = keccak256("ADMIN_ROLE");
    bytes32 public constant WARDEN_ROLE = keccak256("BRIDGE_WARDEN_ROLE");
	mapping( address => bool) public approved;
	address[] public tokens;

	event Deposit( address indexed token, address indexed recipient, uint256 amount );
	event Withdrawal( address indexed token, address indexed recipient, uint256 amount );
	event Registration( address indexed token );

    constructor( address admin ) {
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(ADMIN_ROLE, admin);
        _grantRole(WARDEN_ROLE, admin);

    }

	function deposit(address _token, address _recipient, uint256 _amount ) public {
		// Check if token is registered
		require(approved[_token], "Token not registered");
        
        	// Transfer tokens from sender to this contract using transferFrom
	        ERC20 token = ERC20(_token);
        	require(token.transferFrom(msg.sender, address(this), _amount), "Transfer failed");
        
        	// Emit deposit event
	        emit Deposit(_token, _recipient, _amount);	
	}

	function withdraw(address _token, address _recipient, uint256 _amount ) onlyRole(WARDEN_ROLE) public {
		// Transfer tokens to recipient
	        ERC20 token = ERC20(_token);
	        require(token.transfer(_recipient, _amount), "Transfer failed");
        
        	// Emit withdrawal event
	        emit Withdrawal(_token, _recipient, _amount);	
	}

	function registerToken(address _token) onlyRole(ADMIN_ROLE) public {
		// Check token is not already registered
	        require(!approved[_token], "Token already registered");
        
	        // Add token to approved mapping and tokens array
	        approved[_token] = true;
	        tokens.push(_token);
        
	        // Emit registration event
	        emit Registration(_token);	
	}
}


