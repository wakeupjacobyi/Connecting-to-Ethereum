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

    print(f"Scanning blocks {start_block} - {end_block} on {chain}")

    # Initialize DataFrame
    try:
        df = pd.read_csv(eventfile)
        # Rename column if it exists
        if 'transaction_hash' in df.columns:
            df = df.rename(columns={'transaction_hash': 'transactionHash'})
    except FileNotFoundError:
        df = pd.DataFrame(
            columns=['chain', 'block_number', 'token', 'recipient', 'amount',
                     'transactionHash'])

    if end_block - start_block < 30:
        event_filter = contract.events.Deposit.create_filter(fromBlock=start_block,toBlock=end_block,argument_filters=arg_filter)
        events = event_filter.get_all_entries()
        #print( f"Got {len(events)} entries for block {block_num}" )
        # YOUR CODE HERE
        if len(events) > 0:
            for event in events:
                new_row = {
                    'chain': chain,
                    'block_number': event.blockNumber,
                    'token': event.args.token,
                    'recipient': event.args.recipient,
                    'amount': event.args.amount,
                    'transactionHash': event.transactionHash.hex()
                }
                df.loc[len(df)] = new_row
    else:
        for block_num in range(start_block,end_block+1):
            event_filter = contract.events.Deposit.create_filter(fromBlock=block_num,toBlock=block_num,argument_filters=arg_filter)
            events = event_filter.get_all_entries()
            #print( f"Got {len(events)} entries for block {block_num}" )
            # YOUR CODE HERE

            if len(events) > 0:
                for event in events:
                    new_row = {
                        'chain': chain,
                        'block_number': event.blockNumber,
                        'token': event.args.token,
                        'recipient': event.args.recipient,
                        'amount': event.args.amount,
                        'transactionHash': event.transactionHash.hex()
                    }
                    df.loc[len(df)] = new_row

    df.to_csv(eventfile, index=False)
    return df
