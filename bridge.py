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

    # Connect to appropriate chains and get contract info
    if chain == 'source':
        w3 = connectTo('avax')
        contract_data = getContractInfo('source')
        watching_chain = 'source'
        action_chain = 'destination'
        retry_delay = 1  # shorter delay for AVAX
        max_retries = 3
    else:
        w3 = connectTo('bsc')
        contract_data = getContractInfo('destination')
        watching_chain = 'destination'
        action_chain = 'source'
        retry_delay = 3  # longer delay for BSC
        max_retries = 5

    # Create contract instance for the chain we're watching
    watching_contract = w3.eth.contract(
        address=w3.to_checksum_address(contract_data['address']),
        abi=contract_data['abi']
    )

    # Get contract instance for the chain we'll call functions on
    action_w3 = connectTo('avax' if action_chain == 'source' else 'bsc')
    action_contract_data = getContractInfo(action_chain)
    action_contract = action_w3.eth.contract(
        address=action_w3.to_checksum_address(action_contract_data['address']),
        abi=action_contract_data['abi']
    )

    # Set up account for transactions
    private_key = '0x3077c2142570543b96c1d396cb50bff8602c207d3ea090ace8ad6da01c903927'
    account = action_w3.eth.account.from_key(private_key)

    # Get current block number with retry logic
    for attempt in range(max_retries):
        try:
            time.sleep(retry_delay)  # Wait before each attempt
            current_block = w3.eth.block_number
            from_block = max(current_block - 4,
                             0)  # Last 5 blocks including current
            break
        except Exception as e:
            if attempt == max_retries - 1:
                print(
                    f"Failed to get block number after {max_retries} attempts: {e}")
                return
            continue

    if chain == 'source':
        try:
            time.sleep(retry_delay)
            deposit_events = watching_contract.events.Deposit().get_logs(
                fromBlock=from_block,
                toBlock=current_block
            )

            for event in deposit_events:
                try:
                    time.sleep(retry_delay)  # Wait between transactions
                    # Build transaction
                    nonce = action_w3.eth.get_transaction_count(
                        account.address)
                    gas_price = action_w3.eth.gas_price

                    tx = action_contract.functions.wrap(
                        event['args']['token'],
                        event['args']['recipient'],
                        event['args']['amount']
                    ).build_transaction({
                        'from': account.address,
                        'gas': 200000,
                        'gasPrice': gas_price,
                        'nonce': nonce,
                    })

                    # Sign and send transaction
                    signed_tx = action_w3.eth.account.sign_transaction(tx,
                                                                       private_key)
                    tx_hash = action_w3.eth.send_raw_transaction(
                        signed_tx.rawTransaction)
                    receipt = action_w3.eth.wait_for_transaction_receipt(
                        tx_hash)
                    print(
                        f"Wrapped {event['args']['amount']} tokens for {event['args']['recipient']}")

                except Exception as e:
                    print(f"Failed to wrap tokens: {e}")

        except Exception as e:
            print(f"Failed to get Deposit events: {e}")

    else:  # destination chain
        for attempt in range(max_retries):
            try:
                time.sleep(retry_delay * (attempt + 1))  # Exponential backoff
                unwrap_events = watching_contract.events.Unwrap().get_logs(
                    fromBlock=from_block,
                    toBlock=current_block
                )

                for event in unwrap_events:
                    try:
                        time.sleep(retry_delay)  # Wait between transactions
                        # Cache frequently accessed values
                        nonce = action_w3.eth.get_transaction_count(
                            account.address)
                        gas_price = action_w3.eth.gas_price

                        tx = action_contract.functions.withdraw(
                            event['args']['underlying_token'],
                            event['args']['to'],
                            event['args']['amount']
                        ).build_transaction({
                            'from': account.address,
                            'gas': 200000,
                            'gasPrice': gas_price,
                            'nonce': nonce,
                        })

                        # Sign and send transaction
                        signed_tx = action_w3.eth.account.sign_transaction(tx,
                                                                           private_key)
                        tx_hash = action_w3.eth.send_raw_transaction(
                            signed_tx.rawTransaction)
                        receipt = action_w3.eth.wait_for_transaction_receipt(
                            tx_hash)
                        print(
                            f"Withdrew {event['args']['amount']} tokens for {event['args']['to']}")

                    except Exception as e:
                        print(f"Failed to withdraw tokens: {e}")
                        continue

                # If we got here without exception, break the retry loop
                break

            except Exception as e:
                if attempt == max_retries - 1:
                    print(
                        f"Failed to get Unwrap events after {max_retries} attempts: {e}")
                    return
                continue
