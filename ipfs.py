import requests
import json
import time

# Pinata credentials
PINATA_API_KEY = "3607ed6d2305ff077710"
PINATA_SECRET_KEY = "eb60f6983a453fcbdd12494a8c8950ac207e679d2ec85a04784f5ac72b0c394f"

# Base URLs
PINATA_API_URL = "https://api.pinata.cloud"

# List of IPFS gateways to try
GATEWAYS = [
    "https://gateway.pinata.cloud/ipfs",
    "https://ipfs.io/ipfs",
    "https://cloudflare-ipfs.com/ipfs",
    "https://gateway.moralisipfs.com/ipfs"
]


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
        return response.json()['IpfsHash']
    else:
        raise Exception(f"Error pinning to IPFS: {response.text}")


def get_from_ipfs(cid, content_type="json"):
    assert isinstance(cid,
                      str), f"get_from_ipfs accepts a cid in the form of a string"

    # Try multiple times with increasing delays
    max_retries = 3
    delays = [1, 2, 4]  # Exponential backoff

    last_exception = None

    # Try each gateway
    for gateway in GATEWAYS:
        # Try multiple times with delays
        for retry in range(max_retries):
            try:
                url = f"{gateway}/{cid}"
                response = requests.get(url, timeout=10)

                if response.status_code == 200:
                    data = json.loads(response.text)
                    assert isinstance(data,
                                      dict), f"get_from_ipfs should return a dict"
                    return data

            except (
                    requests.exceptions.RequestException,
                    json.JSONDecodeError) as e:
                last_exception = e

                # Only delay if we're going to try again
                if retry < max_retries - 1:
                    time.sleep(delays[retry])
                continue

    # If we get here, all attempts failed
    raise Exception(f"Error fetching from IPFS: {str(last_exception)}")
