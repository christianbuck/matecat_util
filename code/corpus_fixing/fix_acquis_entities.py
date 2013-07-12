#!/usr/bin/env python

import sys
from htmlentitydefs import name2codepoint
import re
import codecs
import locale

# from http://wiki.python.org/moin/EscapingHtml
def htmlentitydecode(s):
    return re.sub('%s(%s)%s' % ('%','|'.join(name2codepoint),'%'), lambda m: unichr(name2codepoint[m.group(1)]), s)

def has_entities(s):
    return len(re.findall('%s(%s)%s' % ('%','|'.join(name2codepoint),'%'), s))

n_fixed, n_lines, n_entities = 0, 0, 0
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-l', '-locale', action='store_true', dest="use_locale",
                        help='use encoding of locale', default=False)
    args = parser.parse_args(sys.argv[1:])

    if args.use_locale:
        sys.stdin = codecs.getreader(locale.getpreferredencoding())(sys.stdin)
        sys.stdout = codecs.getwriter(locale.getpreferredencoding())(sys.stdout)
    else:
        sys.stdin = codecs.getreader('UTF-8')(sys.stdin)
        sys.stdout = codecs.getwriter('UTF-8')(sys.stdout)

    for linenr, line in enumerate(sys.stdin):
        n_lines += 1
        n = has_entities(line)
        n_entities += n
        if n > 0:
            n_fixed += 1
        sys.stdout.write(htmlentitydecode(line))

    if n_lines > 0:
        sys.stderr.write("fixed %s entities in %s of %s lines (%0.2f%%).\n"
                         %(n_entities, n_fixed, n_lines, 100.*n_fixed/n_lines))
