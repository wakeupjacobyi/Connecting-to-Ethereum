import requests
import json

def pin_to_ipfs(data):
	assert isinstance(data,dict), f"Error pin_to_ipfs expects a dictionary"
	# Convert the Python dictionary to JSON
	json_data = json.dumps(data)

	# Prepare the payload for the request
	files = {'file': ('data.json', json_data)}

	# Send the POST request to Infura's IPFS API
	response = requests.post(INFURA_URL, files=files)

	if response.status_code == 200:
		# Extract and return the CID from the response
		return response.json()['Hash']
	else:
		raise Exception("Error pinning to IPFS: " + response.text)

	return cid

def get_from_ipfs(cid,content_type="json"):
	assert isinstance(cid,str), f"get_from_ipfs accepts a cid in the form of a string"
	#YOUR CODE HERE	

	assert isinstance(data,dict), f"get_from_ipfs should return a dict"
	return data


