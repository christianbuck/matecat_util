#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
from collections import defaultdict
from itertools import imap, izip
import codecs
from writer import write_numbers
import re

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-write', action='store', help="write linenr of offending lines to file")
    parser.add_argument('-n', action='store', type=int, default=3,
                        help="maximum number of 'strange' characters (default: 3)")
    parser.add_argument('-v', action='store_true', dest='verbose',
                        help='verbose (default:off)', default=False)
    parser.add_argument('-i', '-ignore_whitespace', action='store_true', dest="no_ws",
                        help='ignore all whitespace characters including tabs', default=False)
    parser.add_argument('-u', '-uniq', action='store_true', dest="uniq",
                        help='report each character only once', default=False)
    args = parser.parse_args(sys.argv[1:])

    # english standard characters
    chars = set(u"abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ")

    # numbers
    chars.update(set(u"0123456789"))

    # spaces (only regular space)
    chars.update(set(u" "))

    # general non-alphanumeric
    chars.update(set(u"-_*°:.,;?¿!¡%@\\#()[]{}<>+=|/'&\""))

    # currencies
    chars.update(set(u"$€£"))

    # bullet
    chars.update(set(u"•"))

    # intellectual property
    chars.update(set(u"©®™"))

    # foreign characters
    chars.update(set(u"ñçóíîôúÚáœâàéèêüäöÉÄÜÁÀÖß"))

    # mathematical
    chars.update(set(u"½¼¾²³ⁿ±%‰‱≥≤"))

    # quotation
    chars.update(set(u"“”"))

    in_stream = codecs.getreader("utf-8")(sys.stdin)   # read from stdin
    out_stream = codecs.getwriter("utf-8")(sys.stdout) # write to stdout

    re_whitespace = re.compile("\s+")

    strange_lines = []
    for linenr, line in enumerate(in_stream):
        line = line.strip()
        if args.no_ws:
            line = re_whitespace.sub(line, " ")
        # strange_chars = set(line) - chars
        strange_chars = [c for c in line if not c in chars]
        if len(strange_chars) > 3:
            #print strange_chars
            if args.verbose:
                out_stream.write(u"line %s offending characters:" %(linenr))
                if args.uniq:
                    strange_chars = set(strange_chars)
                for c in strange_chars:
                    out_stream.write(u" %s (%s)" %(c, repr(c)))
                out_stream.write(u"\n")
                out_stream.write(line + u"\n")
            strange_lines.append(linenr)

            # print u" ".join(list(linenr, set(line) - chars), " orig:", line

    sys.stdout.write("found %s lines\n" %(len(strange_lines)))
    if args.write:
        write_numbers(strange_lines, args.write)
