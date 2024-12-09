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

    # Setup remains the same
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

    private_key = '0x3077c2142570543b96c1d396cb50bff8602c207d3ea090ace8ad6da01c903927'
    account = action_w3.eth.account.from_key(private_key)

    try:
        if chain == 'source':
            # For source chain, check only the latest block
            current_block = w3.eth.block_number
            block = w3.eth.get_block(current_block)

            for tx_hash in block['transactions']:
                receipt = w3.eth.get_transaction_receipt(tx_hash)
                if receipt['to'] and receipt[
                    'to'].lower() == watching_contract.address.lower():
                    for log in receipt.logs:
                        try:
                            event = watching_contract.events.Deposit().process_log(
                                log)
                            if event:
                                nonce = action_w3.eth.get_transaction_count(
                                    account.address)
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
                                signed_tx = action_w3.eth.account.sign_transaction(
                                    tx, private_key)
                                tx_hash = action_w3.eth.send_raw_transaction(
                                    signed_tx.rawTransaction)
                                receipt = action_w3.eth.wait_for_transaction_receipt(
                                    tx_hash)
                                print(
                                    f"Wrapped {event['args']['amount']} tokens for {event['args']['recipient']}")
                        except:
                            continue

        else:  # destination chain section
            try:
                # Get the specific block where the unwrap happened
                receipt = w3.eth.get_transaction_receipt(w3.eth.block_number)
                contract_address = watching_contract.address.lower()

                # Check if this transaction was to our contract
                if receipt and receipt['to'] and receipt[
                    'to'].lower() == contract_address:
                    # Process all logs from this transaction
                    for log in receipt.logs:
                        if log['address'].lower() == contract_address:
                            # Try to decode as Unwrap event
                            try:
                                event = watching_contract.events.Unwrap().process_log(
                                    log)
                                if event:
                                    # Build and send withdraw transaction
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

                                    signed_tx = action_w3.eth.account.sign_transaction(
                                        withdraw_tx, private_key)
                                    tx_hash = action_w3.eth.send_raw_transaction(
                                        signed_tx.rawTransaction)
                                    receipt = action_w3.eth.wait_for_transaction_receipt(
                                        tx_hash)
                                    print(
                                        f"Withdrew {event['args']['amount']} tokens for {event['args']['to']}")
                            except Exception as e:
                                print(f"Failed to process log: {e}")
            except Exception as e:
                print(f"Error in destination chain processing: {e}")
                