#!/usr/bin/python

import urllib
import sys

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-utf8', action='store_true', help='intepret input a utf-8')
    parser.add_argument('-plus', action='store_true', help='use plus for spaces')
    args = parser.parse_args(sys.argv[1:])


    for line in sys.stdin:
        if args.utf8:
            line = line.decode('utf-8')
        if args.plus:
            print urllib.quote_plus(line.encode('utf-8'))
        else:
            print urllib.quote(line.encode('utf-8'))
