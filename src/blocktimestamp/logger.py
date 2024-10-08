import logging

logger = logging.getLogger('web3-blocktimestamp')
logger.setLevel(level=logging.WARNING)
formatter = logging.Formatter('%(levelname)s@%(name)s : %(message)s')

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)

logger.addHandler(stream_handler)
