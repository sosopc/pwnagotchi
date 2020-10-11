import zlib
import itertools


def compress(payload):
    return zlib.compress(payload, level=zlib.Z_BEST_COMPRESSION)


def decompress(payload):
    return zlib.decompress(payoad)


def chunked_iterable(iterable, size):
    it = iter(iterable)
    while True:
        chunk = tuple(itertools.islice(it, size))
        if not chunk:
            break
        yield chunk

