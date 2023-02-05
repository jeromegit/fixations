# Lazy generation of a short string ID based on an optionally provided string
#  . random shuffle the provided string if requested
#  . generate md5 hash from the passed string
#  . convert the md5 hash into its hex equivalent and turn it into an int
#  . use divmod() to do the equivalent of a long division using the size of the alphabet as denominator
#     . iterate thru the division to create the short_string one char at a time
#     . use the remainder as an index to the alphabet to obtain the character to add to the short_string
#     . the quotient becomes the numerator for the next divmod()
#  . unless randomize=True, the same passed string will always return the same short string ID

import random
import string
import sys
from hashlib import md5

DEFAULT_ALPHABET = '0123456789' + string.ascii_letters


def get_short_str_id(str_to_encode=None, alphabet=None, randomize=None, length=None):
    if str_to_encode is None or len(str_to_encode) == 0:
        str_to_encode = ''.join(random.choices(string.ascii_letters, k=64))
        randomize = True

    if alphabet is None or len(alphabet) == 0:
        alphabet = DEFAULT_ALPHABET
    alphabet_list = list(alphabet)

    if randomize:
        random.shuffle(alphabet_list)

    base = len(alphabet)
    md5_str = md5(str_to_encode.encode()).hexdigest()
    q = int(md5_str, 16)
    short_str_id = ''
    while q > 0:
        q, r = divmod(q, base)
        short_str_id += alphabet_list[r]

    if length is not None and len(short_str_id) > length:
        short_str_id = short_str_id[:length]

    return short_str_id


if __name__ == '__main__':
    string_to_encode = sys.argv[1] if len(sys.argv) > 1 else 'A quick brown fox jumps over the lazy dog!'

    print(f"Random: {get_short_str_id()}")
    print(f"Use provide string: {get_short_str_id(string_to_encode, length=16)}")
