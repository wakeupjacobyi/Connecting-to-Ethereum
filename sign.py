import eth_account
from web3 import Web3
from eth_account.messages import encode_defunct


def sign(m):
    w3 = Web3()
    # create an eth account and recover the address (derived from the public key) and private key
    acct = eth_account.Account.create()
    eth_address = acct.address
    private_key = acct.key

    # Create a message object that can be signed
    message = encode_defunct(text=m)

    # generate signature
    signed_message = w3.eth.account.sign_message(message,
                                                 private_key=private_key)

    signed_message = None

    assert isinstance(signed_message, eth_account.datastructures.SignedMessage)

    return eth_address, signed_message
