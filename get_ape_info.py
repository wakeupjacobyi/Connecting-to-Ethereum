from web3 import Web3
from web3.contract import Contract
from web3.providers.rpc import HTTPProvider
import requests
import json
import time

bayc_address = "0xBC4CA0EdA7647A8aB7C2061c2E118A18a936f13D"
contract_address = Web3.toChecksumAddress(bayc_address)

#You will need the ABI to connect to the contract
#The file 'abi.json' has the ABI for the bored ape contract
#In general, you can get contract ABIs from etherscan
#https://api.etherscan.io/api?module=contract&action=getabi&address=0xBC4CA0EdA7647A8aB7C2061c2E118A18a936f13D
with open('/home/codio/workspace/abi.json', 'r') as f:
	abi = json.load(f) 

############################
#Connect to an Ethereum node
api_url = "https://mainnet.infura.io/v3/cbc1ac8fd9b14c9f8c3d8d527d835a4c"
provider = HTTPProvider(api_url)
web3 = Web3(provider)

def get_ape_info(apeID):
	assert isinstance(apeID,int), f"{apeID} is not an int"
	assert 1 <= apeID, f"{apeID} must be at least 1"

	data = {'owner': "", 'image': "", 'eyes': "" }

	# Create contract instance
	contract = web3.eth.contract(address=contract_address, abi=abi)

	# Get the owner of the ape
	owner = contract.functions.ownerOf(apeID).call()
	data['owner'] = owner

	# Get the token URI
	token_uri = contract.functions.tokenURI(apeID).call()

	# The token URI is an IPFS URI - we need to fetch the metadata
	if token_uri.startswith('ipfs://'):
		ipfs_hash = token_uri.replace('ipfs://', '')
		metadata_url = f'https://ipfs.io/ipfs/{ipfs_hash}'

		# Get the metadata from IPFS
		response = requests.get(metadata_url)
		if response.status_code == 200:
			metadata = response.json()

			# Extract image URI and eyes attribute
			if 'image' in metadata:
				data['image'] = metadata['image']

			# Find eyes attribute in attributes array
			if 'attributes' in metadata:
				for attr in metadata['attributes']:
					if attr['trait_type'] == 'Eyes':
						data['eyes'] = attr['value']
						break

	assert isinstance(data,dict), f'get_ape_info{apeID} should return a dict' 
	assert all( [a in data.keys() for a in ['owner','image','eyes']] ), f"return value should include the keys 'owner','image' and 'eyes'"
	return data

