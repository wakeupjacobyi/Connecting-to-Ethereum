from web3 import Web3
from eth_account.messages import encode_defunct
import random

def signChallenge( challenge ):

    w3 = Web3()

    #This is the only line you need to modify
    sk = "0x3077c2142570543b96c1d396cb50bff8602c207d3ea090ace8ad6da01c903927"
    # 0xd3f300800f276065e032d8ca4f7a09510ccd0a7c475ea0b02a77e06e961ee61f
    acct = w3.eth.account.from_key(sk)

    signed_message = w3.eth.account.sign_message( challenge, private_key = acct._private_key )

    return acct.address, signed_message.signature


def verifySig():
    """
        This is essentially the code that the autograder will use to test signChallenge
        We've added it here for testing 
    """

    challenge_bytes = random.randbytes(32)

    challenge = encode_defunct(challenge_bytes)
    address, sig = signChallenge( challenge )

    w3 = Web3()

    return w3.eth.account.recover_message( challenge , signature=sig ) == address

if __name__ == '__main__':
    """
        Test your function
    """
    if verifySig():
        print( f"You passed the challenge!" )
    else:
        print( f"You failed the challenge!" )

