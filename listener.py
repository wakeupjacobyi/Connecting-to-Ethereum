from web3 import Web3
from web3.contract import Contract
from web3.providers.rpc import HTTPProvider
from web3.middleware import geth_poa_middleware #Necessary for POA chains
import json
from datetime import datetime
import pandas as pd

eventfile = 'deposit_logs.csv'

def scanBlocks(chain,start_block,end_block,contract_address):
    """
    chain - string (Either 'bsc' or 'avax')
    start_block - integer first block to scan
    end_block - integer last block to scan
    contract_address - the address of the deployed contract

	This function reads "Deposit" events from the specified contract,
	and writes information about the events to the file "deposit_logs.csv"
    """
    if chain == 'avax':
        api_url = f"https://api.avax-test.network/ext/bc/C/rpc" #AVAX C-chain testnet

    if chain == 'bsc':
        api_url = f"https://data-seed-prebsc-1-s1.binance.org:8545/" #BSC testnet

    if chain in ['avax','bsc']:
        w3 = Web3(Web3.HTTPProvider(api_url))
        # inject the poa compatibility middleware to the innermost layer
        w3.middleware_onion.inject(geth_poa_middleware, layer=0)
    else:
        w3 = Web3(Web3.HTTPProvider(api_url))

    DEPOSIT_ABI = json.loads('[ { "anonymous": false, "inputs": [ { "indexed": true, "internalType": "address", "name": "token", "type": "address" }, { "indexed": true, "internalType": "address", "name": "recipient", "type": "address" }, { "indexed": false, "internalType": "uint256", "name": "amount", "type": "uint256" } ], "name": "Deposit", "type": "event" }]')
    contract = w3.eth.contract(address=contract_address, abi=DEPOSIT_ABI)

    arg_filter = {}

    if start_block == "latest":
        start_block = w3.eth.get_block_number()
    if end_block == "latest":
        end_block = w3.eth.get_block_number()

    if end_block < start_block:
        print( f"Error end_block < start_block!" )
        print( f"end_block = {end_block}" )
        print( f"start_block = {start_block}" )
        return

    print(f"Scanning blocks {start_block} - {end_block} on {chain}")

    # Initialize DataFrame to store events
    columns = ['chain', 'block_number', 'token', 'recipient', 'amount',
               'transaction_hash']
    try:
        df = pd.read_csv(eventfile)
    except FileNotFoundError:
        df = pd.DataFrame(columns=columns)

    # Process events in batches if range is small, otherwise process block by block
    if end_block - start_block < 30:
        event_filter = contract.events.Deposit.create_filter(
            fromBlock=start_block,
            toBlock=end_block
        )
        events = event_filter.get_all_entries()
        process_events(events, df, chain)
    else:
        for block_num in range(start_block, end_block + 1):
            event_filter = contract.events.Deposit.create_filter(
                fromBlock=block_num,
                toBlock=block_num
            )
            events = event_filter.get_all_entries()
            process_events(events, df, chain)

    # Save updated DataFrame to CSV
    df.to_csv(eventfile, index=False)


def process_events(events, df, chain):
    """Helper function to process events and add them to DataFrame"""
    for event in events:
        new_row = {
            'chain': chain,
            'block_number': event.blockNumber,
            'token': event.args.token,
            'recipient': event.args.recipient,
            'amount': event.args.amount,
            'transaction_hash': event.transactionHash.hex()
        }
        df.loc[len(df)] = new_row