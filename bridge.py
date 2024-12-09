from web3 import Web3
from web3.contract import Contract
from web3.providers.rpc import HTTPProvider
from web3.middleware import geth_poa_middleware  # Necessary for POA chains
import json
import sys
from pathlib import Path

source_chain = 'avax'
destination_chain = 'bsc'
contract_info = "contract_info.json"


def connectTo(chain):
    if chain == 'avax':
        api_url = f"https://api.avax-test.network/ext/bc/C/rpc"  # AVAX C-chain testnet

    if chain == 'bsc':
        api_url = f"https://data-seed-prebsc-1-s1.binance.org:8545/"  # BSC testnet

    if chain in ['avax', 'bsc']:
        w3 = Web3(Web3.HTTPProvider(api_url))
        # inject the poa compatibility middleware to the innermost layer
        w3.middleware_onion.inject(geth_poa_middleware, layer=0)
    return w3


def getContractInfo(chain):
    """
        Load the contract_info file into a dictinary
        This function is used by the autograder and will likely be useful to you
    """
    p = Path(__file__).with_name(contract_info)
    try:
        with p.open('r') as f:
            contracts = json.load(f)
    except Exception as e:
        print("Failed to read contract info")
        print("Please contact your instructor")
        print(e)
        sys.exit(1)

    return contracts[chain]


def scanBlocks(chain):
    """
        chain - (string) should be either "source" or "destination"
        Scan the last 5 blocks of the source and destination chains
        Look for 'Deposit' events on the source chain and 'Unwrap' events on the destination chain
        When Deposit events are found on the source chain, call the 'wrap' function the destination chain
        When Unwrap events are found on the destination chain, call the 'withdraw' function on the source chain
    """

    import time

    if chain not in ['source', 'destination']:
        print(f"Invalid chain: {chain}")
        return

    print(f"\n=== Starting scan for {chain} chain ===")

    # Connect to appropriate chains and get contract info
    if chain == 'source':
        w3 = connectTo('avax')
        contract_data = getContractInfo('source')
        watching_chain = 'source'
        action_chain = 'destination'
    else:
        w3 = connectTo('bsc')
        contract_data = getContractInfo('destination')
        watching_chain = 'destination'
        action_chain = 'source'

    print(f"Connected to {chain} chain")
    print(f"Contract address: {contract_data['address']}")

    # Create contract instances
    watching_contract = w3.eth.contract(
        address=w3.to_checksum_address(contract_data['address']),
        abi=contract_data['abi']
    )

    action_w3 = connectTo('avax' if action_chain == 'source' else 'bsc')
    action_contract_data = getContractInfo(action_chain)
    action_contract = action_w3.eth.contract(
        address=action_w3.to_checksum_address(action_contract_data['address']),
        abi=action_contract_data['abi']
    )

    # Set up account
    private_key = '0x3077c2142570543b96c1d396cb50bff8602c207d3ea090ace8ad6da01c903927'
    account = action_w3.eth.account.from_key(private_key)
    print(f"Using account: {account.address}")

    if chain == 'source':
        current_block = w3.eth.block_number
        from_block = current_block - 4
        print(
            f"Scanning blocks {from_block} to {current_block} on {chain} chain")

        try:
            deposit_events = watching_contract.events.Deposit().get_logs(
                fromBlock=from_block,
                toBlock=current_block
            )
            print(f"Found {len(deposit_events)} Deposit events")

            for event in deposit_events:
                try:
                    nonce = action_w3.eth.get_transaction_count(
                        account.address)
                    print(
                        f"Processing Deposit: Amount={event['args']['amount']}, Recipient={event['args']['recipient']}")

                    tx = action_contract.functions.wrap(
                        event['args']['token'],
                        event['args']['recipient'],
                        event['args']['amount']
                    ).build_transaction({
                        'from': account.address,
                        'gas': 200000,
                        'gasPrice': action_w3.eth.gas_price,
                        'nonce': nonce,
                    })

                    signed_tx = action_w3.eth.account.sign_transaction(tx,
                                                                       private_key)
                    tx_hash = action_w3.eth.send_raw_transaction(
                        signed_tx.rawTransaction)
                    print(f"Sent wrap transaction: {tx_hash.hex()}")

                    receipt = action_w3.eth.wait_for_transaction_receipt(
                        tx_hash)
                    print(
                        f"Wrap transaction confirmed in block {receipt['blockNumber']}")
                    print(
                        f"Wrapped {event['args']['amount']} tokens for {event['args']['recipient']}")

                except Exception as e:
                    print(f"Failed to wrap tokens: {e}")

        except Exception as e:
            print(f"Failed to get Deposit events: {e}")

    else:  # destination chain (BSC)
        try:
            current_block = w3.eth.block_number
            print(f"Scanning block {current_block} on {chain} chain")

            # Get full block with transactions
            block = w3.eth.get_block(current_block, full_transactions=True)
            print(
                f"Retrieved block with {len(block['transactions'])} transactions")

            contract_address = watching_contract.address.lower()
            print(f"Looking for transactions to contract: {contract_address}")

            found_unwrap = False
            for tx in block['transactions']:
                print(
                    f"\nChecking transaction: {tx.hash.hex() if hasattr(tx, 'hash') else tx['hash']}")

                tx_to = tx.get('to', '').lower() if isinstance(tx,
                                                               dict) else getattr(
                    tx, 'to', '').lower()
                if tx_to == contract_address:
                    print("Found transaction to our contract")

                    # Get transaction receipt
                    receipt = w3.eth.get_transaction_receipt(
                        tx.hash if hasattr(tx, 'hash') else tx['hash'])
                    print(
                        f"Transaction receipt has {len(receipt['logs'])} logs")

                    # Process logs in the receipt
                    for log in receipt.get('logs', []):
                        print(
                            f"Processing log from address: {log['address'].lower()}")

                        if log['address'].lower() == contract_address:
                            try:
                                # Try to decode the log as an Unwrap event
                                event = watching_contract.events.Unwrap().process_log(
                                    log)
                                found_unwrap = True

                                print("\n=== Found Unwrap Event ===")
                                print(
                                    f"Underlying token: {event['args']['underlying_token']}")
                                print(f"To: {event['args']['to']}")
                                print(f"Amount: {event['args']['amount']}")

                                # Build withdraw transaction
                                nonce = action_w3.eth.get_transaction_count(
                                    account.address)
                                withdraw_tx = action_contract.functions.withdraw(
                                    event['args']['underlying_token'],
                                    event['args']['to'],
                                    event['args']['amount']
                                ).build_transaction({
                                    'from': account.address,
                                    'gas': 200000,
                                    'gasPrice': action_w3.eth.gas_price,
                                    'nonce': nonce,
                                })

                                print("Built withdraw transaction")

                                # Sign and send transaction
                                signed_tx = action_w3.eth.account.sign_transaction(
                                    withdraw_tx, private_key)
                                tx_hash = action_w3.eth.send_raw_transaction(
                                    signed_tx.rawTransaction)
                                print(
                                    f"Sent withdraw transaction: {tx_hash.hex()}")

                                receipt = action_w3.eth.wait_for_transaction_receipt(
                                    tx_hash)
                                print(
                                    f"Withdraw transaction confirmed in block {receipt['blockNumber']}")
                                print(
                                    f"Withdrew {event['args']['amount']} tokens for {event['args']['to']}")

                            except Exception as e:
                                print(
                                    f"Failed to process potential Unwrap event: {e}")
                                continue

            if not found_unwrap:
                print("No Unwrap events found in this block")

        except Exception as e:
            print(f"Failed to process block: {e}")