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

from .blocktimestamp import BlockTimestamp, Block

def timestamp_to_block(w3, timestamp: int) -> Block: 
    block_timestamp_object = BlockTimestamp(w3)
    block = block_timestamp_object.timestamp_to_block(timestamp)
    return block
