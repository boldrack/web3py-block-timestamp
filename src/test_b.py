import time
from blocktimestamp import Block, BlockTimestamp
from web3 import Web3

if __name__ == '__main__':
    w3 = Web3(Web3.HTTPProvider('https://mainnet.infura.io/v3/150f226ab302441a9457a1ae5e1db5b4'))
    w3.is_connected()

    bt = BlockTimestamp(w3)
    ts = int(time.time()) - 94608000#(3600 * 10 ) 
    res = bt.timestamp_to_block(ts)


