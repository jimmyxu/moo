#!/usr/bin/env python3

import hashlib
import sys

def main(args):
    source = open(args[0], 'rb')
    keyData = b' '.join([x.encode('utf-8') for x in args[1:]])
    keyData = hashlib.sha1(keyData).digest()

    # https://www.w3.org/publishing/epub3/epub-ocf.html#obfus-algorithm
    outer = 0
    while outer < 52:
        inner = 0
        while inner < 20:
            sourceByte = source.read(1)
            if sourceByte == b'':
                break
            keyByte = keyData[inner]
            obfuscatedByte = ord(sourceByte) ^ keyByte
            sys.stdout.buffer.write(bytes([obfuscatedByte]))
            inner += 1
        outer += 1

    sys.stdout.buffer.write(source.read())


if __name__ == '__main__':
    main(sys.argv[1:])
