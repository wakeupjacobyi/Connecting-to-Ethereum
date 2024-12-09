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
    if chain not in ['source', 'destination']:
        print(f"Invalid chain: {chain}")
        return

    if chain == 'source':
        w3 = connectTo('avax')
        contract_data = getContractInfo('source')
        action_chain = 'destination'
    else:
        w3 = connectTo('bsc')
        contract_data = getContractInfo('destination')
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
        current_block = w3.eth.block_number
        print(f"Scanning block {current_block}")

        if chain == 'source':
            # For source chain, get the latest block's transactions
            block = w3.eth.get_block(current_block, full_transactions=True)

            for tx in block['transactions']:
                # Check if transaction is to our contract
                if isinstance(tx, dict) and tx.get('to') and tx[
                    'to'].lower() == watching_contract.address.lower():
                    receipt = w3.eth.get_transaction_receipt(tx['hash'])

                    # Process logs for Deposit events
                    for log in receipt['logs']:
                        if log[
                            'address'].lower() == watching_contract.address.lower():
                            try:
                                deposit_event = watching_contract.events.Deposit().process_log(
                                    log)
                                if deposit_event:
                                    # Handle Deposit event
                                    nonce = action_w3.eth.get_transaction_count(
                                        account.address)
                                    wrap_tx = action_contract.functions.wrap(
                                        deposit_event['args']['token'],
                                        # Using 'token' from Deposit event
                                        deposit_event['args']['recipient'],
                                        deposit_event['args']['amount']
                                    ).build_transaction({
                                        'from': account.address,
                                        'gas': 200000,
                                        'gasPrice': action_w3.eth.gas_price,
                                        'nonce': nonce,
                                    })

                                    signed_tx = action_w3.eth.account.sign_transaction(
                                        wrap_tx, private_key)
                                    tx_hash = action_w3.eth.send_raw_transaction(
                                        signed_tx.rawTransaction)
                                    receipt = action_w3.eth.wait_for_transaction_receipt(
                                        tx_hash)
                                    print(
                                        f"Wrapped {deposit_event['args']['amount']} tokens for {deposit_event['args']['recipient']}")
                            except Exception as e:
                                continue

        else:
            # For destination chain, get just the latest block
            block = w3.eth.get_block(current_block)
            if block and block['transactions']:
                latest_tx = block['transactions'][
                    -1]  # Get the last transaction
                receipt = w3.eth.get_transaction_receipt(latest_tx)

                if receipt and receipt['to'] and receipt[
                    'to'].lower() == watching_contract.address.lower():
                    for log in receipt['logs']:
                        if log[
                            'address'].lower() == watching_contract.address.lower():
                            try:
                                unwrap_event = watching_contract.events.Unwrap().process_log(
                                    log)
                                if unwrap_event:
                                    # Handle Unwrap event
                                    nonce = action_w3.eth.get_transaction_count(
                                        account.address)
                                    withdraw_tx = action_contract.functions.withdraw(
                                        unwrap_event['args'][
                                            'underlying_token'],
                                        # Using 'underlying_token' from Unwrap event
                                        unwrap_event['args']['to'],
                                        unwrap_event['args']['amount']
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
                                        f"Withdrew {unwrap_event['args']['amount']} tokens for {unwrap_event['args']['to']}")
                            except Exception as e:
                                continue

    except Exception as e:
        print(f"Error running scanBlocks('{chain}')")
        print(str(e))
        