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

    if chain not in ['source', 'destination']:
        print(f"Invalid chain: {chain}")
        return

    w3 = connectTo('avax' if chain == 'source' else 'bsc')
    contract_data = getContractInfo('source' if chain == 'source' else 'destination')
    watching_contract = w3.eth.contract(
        address=w3.to_checksum_address(contract_data['address']),
        abi=contract_data['abi']
    )

    action_w3 = connectTo('bsc' if chain == 'source' else 'avax')
    action_contract_data = getContractInfo('destination' if chain == 'source' else 'source')
    action_contract = action_w3.eth.contract(
        address=action_w3.to_checksum_address(action_contract_data['address']),
        abi=action_contract_data['abi']
    )

    private_key = '<PRIVATE_KEY>'
    account = action_w3.eth.account.from_key(private_key)

    current_block = w3.eth.block_number

    try:
        if chain == 'source':
            deposit_events = watching_contract.events.Deposit().get_logs(
                fromBlock=current_block - 5,
                toBlock=current_block
            )

            for event in deposit_events:
                tx = action_contract.functions.wrap(
                    event['args']['token'],
                    event['args']['recipient'],
                    event['args']['amount']
                ).build_transaction({
                    'from': account.address,
                    'gas': 300000,
                    'gasPrice': action_w3.eth.gas_price,
                    'nonce': action_w3.eth.get_transaction_count(account.address),
                })
                signed_tx = action_w3.eth.account.sign_transaction(tx, private_key)
                tx_hash = action_w3.eth.send_raw_transaction(signed_tx.rawTransaction)
                action_w3.eth.wait_for_transaction_receipt(tx_hash)
                print(f"Wrapped {event['args']['amount']} tokens for {event['args']['recipient']}")

        else:
            unwrap_events = watching_contract.events.Unwrap().get_logs(
                fromBlock=current_block - 5,
                toBlock=current_block
            )

            for event in unwrap_events:
                tx = action_contract.functions.withdraw(
                    event['args']['underlying_token'],
                    event['args']['to'],
                    event['args']['amount']
                ).build_transaction({
                    'from': account.address,
                    'gas': 300000,
                    'gasPrice': action_w3.eth.gas_price,
                    'nonce': action_w3.eth.get_transaction_count(account.address),
                })
                signed_tx = action_w3.eth.account.sign_transaction(tx, private_key)
                tx_hash = action_w3.eth.send_raw_transaction(signed_tx.rawTransaction)
                action_w3.eth.wait_for_transaction_receipt(tx_hash)
                print(f"Withdrew {event['args']['amount']} tokens for {event['args']['to']}")

    except Exception as e:
        print(f"Error processing blocks for {chain}: {e}")
