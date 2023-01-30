# inspired by https://code.activestate.com/recipes/576918/
#
import sys
from hashlib import md5

DEFAULT_ALPHABET = 'mn6j2c4rv8bpygw95z7hsdaetxuk3fq'
DEFAULT_BLOCK_SIZE = 24
MIN_LENGTH = 5


class TinyStringEncoder(object):
    def __init__(self, alphabet=DEFAULT_ALPHABET, block_size=DEFAULT_BLOCK_SIZE):
        self.alphabet = alphabet
        self.block_size = block_size
        self.mask = (1 << block_size) - 1
        self.mapping = range(block_size, 0)

    def encode_str(self, n, min_length=MIN_LENGTH):
        return self.enbase(self.encode(n), min_length)

    def decode_str(self, n):
        return self.decode(self.debase(n))

    def encode(self, n):
        return (n & ~self.mask) | self._encode(n & self.mask)

    def _encode(self, n):
        result = 0
        for i, b in enumerate(self.mapping):
            if n & (1 << i):
                result |= (1 << b)
        return result

    def decode(self, n):
        return (n & ~self.mask) | self._decode(n & self.mask)

    def _decode(self, n):
        result = 0
        for i, b in enumerate(self.mapping):
            if n & (1 << b):
                result |= (1 << i)
        return result

    def enbase(self, x, min_length=MIN_LENGTH):
        result = self._enbase(x)
        padding = self.alphabet[0] * (min_length - len(result))
        return '%s%s' % (padding, result)

    def _enbase(self, x):
        n = len(self.alphabet)
        if x < n:
            return self.alphabet[x]
        return self._enbase(x / n) + self.alphabet[x % n]

    def debase(self, x):
        n = len(self.alphabet)
        result = 0
        for i, c in enumerate(reversed(x)):
            result += self.alphabet.index(c) * (n ** i)
        return result


DEFAULT_ENCODER = TinyStringEncoder()


def encode(n):
    return DEFAULT_ENCODER.encode(n)


def decode(n):
    return DEFAULT_ENCODER.decode(n)


def enbase(n, min_length=MIN_LENGTH):
    return DEFAULT_ENCODER.enbase(n, min_length)


def debase(n):
    return DEFAULT_ENCODER.debase(n)


def encode_str(n, min_length=MIN_LENGTH):
    return DEFAULT_ENCODER.encode_str(n, min_length)


def decode_str(n):
    return DEFAULT_ENCODER.decode_str(n)


if __name__ == '__main__':
    str_to_encode = sys.argv[1] if len(sys.argv) > 1 else 'A quick brown fox jumps over the lazy dog'
    tiny_encoded = encode_str(123)
    str_md5 = md5(str_to_encode.encode()).hexdigest()
    print(f"before:{str_to_encode} and after:{str_md5}")
