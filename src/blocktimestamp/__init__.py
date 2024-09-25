'''
what we doing ? 

__get_boundaries

_get_date (date: datetime.datetime ) : 

BlockTimestampResponse: wrapper for a typical response ( block, ts, [after, before] )

explain `before` and `after` in the context of this solution . 
`after` -> The block must be same or after the date ...[]..TS..[x]....[]....[]
`before` -> The block must before the date ...[]....[x]..TS..[]....[]

logging 
exception 
'''
import datetime
from dataclasses import dataclass, field
from typing import Union

@dataclass
class BlockTimestampData:
    block: int
    timestamp: int
    hash: str = field(default_factory=str)

@dataclass
class Block:
    number: int
    timestamp: int
    hash: str = field(default_factory=str)

class BlockTimestamp(object):
    def __init__(self, channel): # the channel gonna be web3
        self._channel = channel
        self._latest = None
        self._genesis = None
        self._block_time = None 
        self._setup()

    
    def _setup(self):
        '''
        set up 
        '''
        self._latest = self._get_block('latest')
        self._genesis = self._get_block(1)
        self._block_time = self._get_blocktime(self._genesis, self._latest)

        print(f'{self._genesis=} {self._latest=} {self._block_time=}')

    def _web3_get_block(self, identifier) -> Block:
        '''
        web3 lib specific method to get the block. we might have others hence 
        why we need a specific. the wrapper being `get_block`
        '''
        res = self._channel.eth.get_block(identifier)
        return Block(res.number, res.timestamp)


    def _get_block(self, identifier: Union[str, int]):
        '''
        get the block and save in an internal cache to save request 
        '''
        # also do cache
        return self._web3_get_block(identifier)


    def _get_blocktime_raw(self, start: int, latest: int, start_n: int, latest_n: int) -> int:
        return int((latest - start) / latest_n - start_n)


    def _get_blocktime(self, genesis: Block, latest: Block) -> int:
        '''
        what's this trying to achieve, 
        blocktime = latest.ts - start.ts ) / latest.number - genesis.number
        that's the ; total timestamp / block count 
        # return int((latest.timestamp - genesis.timestamp) / ( latest.number - genesis.number))
        '''
        return self._get_blocktime_raw(genesis.timestamp, latest.timestamp, genesis.number, latest.number)


    def _datetime_isbefore(self, date_ts: int, date_ts_b: int):
        '''
        returns if time is before another ;
        why create an entire method for this is we can also process `datetime` 
        '''
        return date_ts < date_ts_b


    def _datetime_isafter(self, date_ts: int, date_ts_b: int): 
        '''
        returns if time is after another
        '''
        return date_ts > date_ts_b



    def _get_predicted_block(self, target_ts: int, genesis: Block, blocktime: int) -> Block:
        '''
        does the prediction of incrementing the block by the number block time that has passed 
        till current timestamp or now.
        now_timestamp - firstblock.timestamp ) / blocktime 
        '''
        blocknumber = int(( target_ts - genesis.timestamp )  / blocktime)
        print('_get_predicteD_block(): ', blocknumber, target_ts)
        return self._get_block(blocknumber)


    def _is_better_block(self, timestamp: int, block: Block) -> bool:
        '''
        Parameters:
        ----------
        timestamp: [datetime.datetime, int] -> The target timestamp 
        block: [int] -> The block to be assessed for good fit 

        Returns:
        -------
        bool - indicates if the block is a better fit to be used as a result for the target timestamp 

        Note: 
        ----
        see header comment for description of `after` and `before`

        - Assuming `after`. 
        return False if the timestamp of the predicted block is before the date/timestamp target
        since we only need blocks after it

        return True if the timestamp of the predicted block is same or after the target timestamp and 
        also but also the target timestamp is greater than the timestamp of the previous block
        ...[w]..TS..[x]... (w is the previous block)

        - Assuming `before`. 
        ---
        return False if the timestamp of the predicted block is same or after the date/timestamp target
        since we only need blocks before it

        return True if the the timestamp of the predicted block is before the target timestamp and also the
        target timestamp is lesser than the timestamp of the next block
        ...[x]..TS..[w].. ( w is the next block )
        '''
        print(f'_is_better_bloc(): {timestamp=}, {block=}')
        if block.timestamp >= timestamp: return False
        # block has to be before
        next_block = self._get_block(block.number + 1)
        return block.timestamp < timestamp < next_block.timestamp
        # account for `after` and `before`



    def _find_better(self, predicted_block: Block, target_ts: int, blocktime=12):
        '''
        a recursive function that does the main work here. it takes in the predicted block from 
        `_get_predicted_block` . 
        '''
        print(f'_find_better({predicted_block=}, {target_ts=})')
        print(datetime.datetime.fromtimestamp(predicted_block.timestamp))

        # return early if our target timestamp lies within the predicted block and it's 
        # forward neighbor . Also account for backward neighbor in case of `after`
        if self._is_better_block(target_ts, predicted_block): return predicted_block

        # get difference in timestamp between the predicted block and our target
        # this could be positive or negative depending on the pos of the predicted block
        ts_diff = target_ts - predicted_block.timestamp

        # calculate how many block we moving up or down based on previous block time
        block_steps = ts_diff // blocktime
        print(f'{block_steps=}')

        # get the predicted block based on the just calculated block steps
        new_block_nmb = predicted_block.number + block_steps
        new_predicted_block = self._get_block(new_block_nmb)

        return self._find_better(new_predicted_block, target_ts)


    def block_to_timestamp(self, identifier):
        block = self._get_block(identifier)
        return block.timestamp


    def timestamp_to_block(self, timestamp: int): 
        '''
        return first block if timestamp is before first block timestamp
        return latest block if timetamp is after or equal latest block timestamp 
        '''
        print('timestamp_to_block();', datetime.datetime.fromtimestamp(timestamp))

        if not (self._genesis and self._latest): 
            raise Exception('No Genesis or latest setup')
            # return # raise proper exception

        if not self._block_time: 
            raise Exception('No blocktime computed')
            return # confirm we also get the block time 

        # return first block if timestamp is before first block timestamp
        if timestamp < self._genesis.timestamp: 
            print('return genesis, timestamp < genesis')
            return self._genesis
        
        # return latest block if timetamp is after or equal latest block timestamp 
        if timestamp > self._latest.timestamp: 
            print('return latest, timestamp > latest')
            return self._latest

        # predict our block position based on known data such as block time
        # we'd be expecting this to get us as close as possible . 
        # we'd known how much time it takes for each block to be created => blocktime
        # so we'd be expecting our block to be closer by how long the block has moved relative to our target
        predicted_block = self._get_predicted_block(timestamp, self._genesis, self._block_time)
        print(f'{predicted_block=}')
        

        # test how close it is . then we start walking through. for the purpose of first iteration
        # we won't be considering `start` . so we'd be assuming `after`. this means the next most situable 
        # block that is created after our timestamp. this is decided as it makes most sense. you most likely
        # would like your data to be bigger than lesser. You can always filter out the unwanted data using 
        # the timestamp compare 
        
        # we now either walk back or forward from the first prediction as well as subsequent prediction 
        # recursively
        return self._find_better(predicted_block, timestamp)

        # # return our block 
        # return predicted_block

