
from logger import logger

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
        self._next_block_records = {}
        self._setup()

    
    def _setup(self):
        '''
        set up 
        '''
        self._latest = self._get_block('latest')
        self._genesis = self._get_block(1)
        self._block_time = self._get_blocktime(self._genesis, self._latest)

        logger.debug(f'{self._genesis=} {self._latest=} {self._block_time=}')


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
        logger.debug(f'{start} {latest} {start_n} {latest_n}')
        try:
            c_blocktime = int((latest - start) / (latest_n - start_n))
        except ZeroDivisionError:
            c_blocktime = int((latest - start) / 1)

        return c_blocktime

    def _get_blocktime(self, genesis: Block, latest: Block) -> int:
        '''
        what's this trying to achieve, 
        blocktime = latest.ts - start.ts ) / latest.number - genesis.number
        that's the ; total timestamp / block count 
        # return int((latest.timestamp - genesis.timestamp) / ( latest.number - genesis.number))
        '''
        return abs(self._get_blocktime_raw(genesis.timestamp, latest.timestamp, genesis.number, latest.number))


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
        logger.debug('_get_predicted_block(): ', blocknumber, target_ts)
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
        logger.debug(f'_is_better_bloc(): {timestamp=}, {block=}')
        # i think it's a good idea to accept it if it's an exact match
        if block.timestamp == timestamp: return True

        # we'd like to reject if the block comes before our TS
        if block.timestamp > timestamp: return False

        # block has to be before
        next_block = self._get_block(block.number + 1)
        return block.timestamp < timestamp < next_block.timestamp

        # account for `after` and `before`



    def _get_next_block(self, timestamp: int, block: Block, skips: int = 0) -> int:
        '''
        basically adds the skip step to the passed block and return the new block number
        but we could have used this inline. we're making this method to help us address the 
        'unclear' bug mentioned before. so this will help us peek at the neighbor whenever 
        we try to walk the same block more than once. this usually indicates the issue is on
        '''
        logger.debug(f'***************** _get_next_block: {timestamp=} {block=} {skips=} ')
        next_block = block.number + skips

        # if the result block gets us past the latest block, we'd just return the latest instead 
        if self._latest and next_block > self._latest.number: return self._latest.number

        # here's the point where we check if we've hit this 'next_block' previously 
        # if that's the case , we'd check recursively check the neighbor. 
        # recursively comes in when the neighbor was previously hit, then we'd hit 
        # the neighbor of the neighbor and goes on. This tends to get us closer to the 
        # target faster than bouncing between two close point 
        if next_block in self._next_block_records[timestamp]: 
            rc_skips = skips-0 if skips  < 0 else skips+1 
            return self._get_next_block(timestamp, block, rc_skips)

        
        # add this 'next_block' to the record so we know when we hit it again 
        # then it can spin into action of asking it's neighbor 
        self._next_block_records[timestamp].append(next_block)

        return next_block if next_block > 0 else 1


    def _find_better(self, predicted_block: Block, target_ts: int, blocktime=12):
        '''
        a recursive function that does the main work here. it takes in the predicted block from 
        `_get_predicted_block` . 
        '''
        logger.debug(f'_find_better({predicted_block=}, {target_ts=}), {datetime.datetime.fromtimestamp(predicted_block.timestamp)}')

        # return early if our target timestamp lies within the predicted block and it's 
        # forward neighbor . Also account for backward neighbor in case of `after`
        if self._is_better_block(target_ts, predicted_block): return predicted_block

        # get difference in timestamp between the predicted block and our target
        # this could be positive or negative depending on the pos of the predicted block
        ts_diff = target_ts - predicted_block.timestamp

        # calculate how many block we moving up or down based on previous block time
        block_steps = ts_diff // blocktime
        logger.debug(f'{block_steps=}')

        # -- ! -- 
        # there's an unclear bug where the recursion flies between 2 different points 
        # can't really explain it yet on a granular level. but can solve it by tickling 
        # to the neighbors 
        # -- ! -- 
        # get the predicted block based on the just calculated block steps
        new_block_nmb = self._get_next_block(target_ts, predicted_block, block_steps)
        new_predicted_block = self._get_block(new_block_nmb)

        # compute a new block time based on the new boundaries 
        # the new predicted block and former predicted block
        new_blocktime = self._get_blocktime(new_predicted_block, predicted_block)
        logger.debug(f' {new_block_nmb=} {new_blocktime=}')


        return self._find_better(new_predicted_block, target_ts)


    def block_to_timestamp(self, identifier):
        block = self._get_block(identifier)
        return block.timestamp


    def timestamp_to_block(self, timestamp: int): 
        '''
        return first block if timestamp is before first block timestamp
        return latest block if timetamp is after or equal latest block timestamp 
        '''
        logger.debug('xxx timestamp_to_block();', datetime.datetime.fromtimestamp(timestamp))

        if not (self._genesis and self._latest): 
            raise Exception('No Genesis or latest setup')
            # return # raise proper exception

        if not self._block_time: 
            raise Exception('No blocktime computed')
            return # confirm we also get the block time 

        # return first block if timestamp is before first block timestamp
        if timestamp < self._genesis.timestamp: 
            logger.warning('return genesis, timestamp < genesis')
            return self._genesis
        
        # return latest block if timetamp is after or equal latest block timestamp 
        if timestamp > self._latest.timestamp: 
            logger.warning('return latest, timestamp > latest')
            return self._latest

        # add a new record for this timestamp to be consumed later by `get_next_block`
        self._next_block_records[timestamp] = []

        # predict our block position based on known data such as block time
        # we'd be expecting this to get us as close as possible . 
        # we'd known how much time it takes for each block to be created => blocktime
        # so we'd be expecting our block to be closer by how long the block has moved relative to our target
        predicted_block = self._get_predicted_block(timestamp, self._genesis, self._block_time)
        logger.debug(f'{predicted_block=}')

        # test how close it is . then we start walking through. for the purpose of first iteration
        # we won't be considering `start` . so we'd be assuming `after`. this means the next most situable 
        # block that is created after our timestamp. this is decided as it makes most sense. you most likely
        # would like your data to be bigger than lesser. You can always filter out the unwanted data using 
        # the timestamp compare 
        
        # we now either walk back or forward from the first prediction as well as subsequent prediction 
        # recursively
        return self._find_better(predicted_block, timestamp)

