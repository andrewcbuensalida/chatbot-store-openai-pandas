import time

from loguru import logger

def with_retries(fn, retries=3, delay=1):
    def wrapper(*args, **kwargs):
        attempt = 0
        while attempt < retries:
            try:
                return fn(*args, **kwargs)
            except Exception as err:
                logger.error(f'Error: {err}')
                attempt += 1
                if attempt >= retries:
                    logger.error('Max retries reached')
                    raise err
                logger.warning(f'Retrying... ({attempt}/{retries})')
                time.sleep(delay)
    return wrapper