import requests
import json

# Pinata credentials
PINATA_API_KEY = "3607ed6d2305ff077710"
PINATA_SECRET_KEY = "eb60f6983a453fcbdd12494a8c8950ac207e679d2ec85a04784f5ac72b0c394f"

# Base URLs
PINATA_API_URL = "https://api.pinata.cloud"
PINATA_GATEWAY = "https://gateway.pinata.cloud/ipfs"


def pin_to_ipfs(data):
    assert isinstance(data, dict), f"Error pin_to_ipfs expects a dictionary"

    # Convert the Python dictionary to JSON
    json_data = json.dumps(data)

    # Set up the headers with API key authentication
    headers = {
        'pinata_api_key': PINATA_API_KEY,
        'pinata_secret_api_key': PINATA_SECRET_KEY
    }

    # Prepare the files for upload
    files = {
        'file': ('data.json', json_data, 'application/json')
    }

    # Send the POST request to Pinata's pinning endpoint
    response = requests.post(
        f"{PINATA_API_URL}/pinning/pinFileToIPFS",
        files=files,
        headers=headers
    )

    if response.status_code == 200:
        # Extract and return the CID (IpfsHash) from the response
        return response.json()['IpfsHash']
    else:
        raise Exception(f"Error pinning to IPFS: {response.text}")


def get_from_ipfs(cid, content_type="json"):
    assert isinstance(cid,
                      str), f"get_from_ipfs accepts a cid in the form of a string"

    # Construct the gateway URL
    url = f"{PINATA_GATEWAY}/{cid}"

    # Send GET request to Pinata gateway
    response = requests.get(url)

    if response.status_code != 200:
        raise Exception(f"Error fetching from IPFS: {response.text}")

    try:
        # Parse the JSON response
        data = json.loads(response.text)
        assert isinstance(data, dict), f"get_from_ipfs should return a dict"
        return data
    except json.JSONDecodeError:
        raise Exception("Error: Retrieved content is not valid JSON")
