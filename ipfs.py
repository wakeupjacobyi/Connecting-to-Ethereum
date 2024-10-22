import requests
import json

# Base URL for Infura IPFS API
INFURA_URL = "https://ipfs.infura.io:5001/api/v0"

INFURA_PROJECT_ID = "9f6ee70719cd48b793e039c59df743cb"
INFURA_PROJECT_SECRET = "pl9fpwhZ7NjsqGtVl6qZZ09fPlYoyNyuZQhXgdw2obms1pINNM5tyg"

# Create basic auth header from project ID and secret
AUTH = (INFURA_PROJECT_ID, INFURA_PROJECT_SECRET)


def pin_to_ipfs(data):
	assert isinstance(data, dict), f"Error pin_to_ipfs expects a dictionary"

	# Convert the Python dictionary to JSON
	json_data = json.dumps(data)

	# Prepare the payload for the request
	files = {'file': ('data.json', json_data)}

	# Send the POST request to Infura's IPFS API with authentication
	response = requests.post(
		f"{INFURA_URL}/add",
		files=files,
		auth=AUTH
	)

	if response.status_code == 200:
		# Extract and return the CID from the response
		return response.json()['Hash']
	else:
		raise Exception("Error pinning to IPFS: " + response.text)


def get_from_ipfs(cid):
	assert isinstance(cid, str), f"get_from_ipfs accepts a cid in the form " \
								f"of a string"
	# Send POST request to Infura's IPFS cat endpoint
	response = requests.post(f"{INFURA_URL}/cat?arg={cid}")

	if response.status_code != 200:
		raise Exception(f"Error fetching from IPFS: {response.text}")

	try:
		# Parse the JSON response
		data = json.loads(response.text)
		assert isinstance(data, dict), f"get_from_ipfs should return a dict"
		return data
	except json.JSONDecodeError:
		raise Exception("Error: Retrieved content is not valid JSON")
