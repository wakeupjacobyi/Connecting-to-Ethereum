from web3 import Web3
from web3.contract import Contract
from web3.providers.rpc import HTTPProvider
import requests

bayc_address = "0xBC4CA0EdA7647A8aB7C2061c2E118A18a936f13D"
contract_address = Web3.toChecksumAddress(bayc_address)

############################
#Get Contract ABI from etherscan
ABI_ENDPOINT = 'https://api.etherscan.io/api?module=contract&action=getabi&address='
try:
	response = requests.get( f"{ABI_ENDPOINT}{contract_address}", timeout = 20 )	
	abi = response.json()
except Exception as e:
	print( f"Failed to get {contract_address} from {ABI_ENDPOINT}" )
	print( e )

bayc_address = "0xBC4CA0EdA7647A8aB7C2061c2E118A18a936f13D"

############################
#Connect to an Ethereum node
token = "Mwb3juVAfI1g2RmA1JCGdYk-2_BmFrnLOtbomP1oDa4"
api_url = f"https://c2emjgrvmi7cabd41mpg.bdnodes.net?auth={token}"
provider = HTTPProvider(api_url)
web3 = Web3(provider)

contract = web3.eth.contract(address=contract_address,abi=abi)
supply = contract.functions.totalSupply().call()

print( f"Supply = {supply}" )