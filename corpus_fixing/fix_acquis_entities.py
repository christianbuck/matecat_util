#!/usr/bin/env python

import sys
from htmlentitydefs import name2codepoint
import re
import codecs
import locale

# from http://wiki.python.org/moin/EscapingHtml
def htmlentitydecode(s):
    return re.sub('%s(%s)%s' % ('%','|'.join(name2codepoint),'%'), lambda m: unichr(name2codepoint[m.group(1)]), s)

if __name__ == "__main__":
    sys.stdin = codecs.getreader(locale.getpreferredencoding())(sys.stdin)
    sys.stdout = codecs.getwriter(locale.getpreferredencoding())(sys.stdout)
    for linenr, line in enumerate(sys.stdin):
        sys.stdout.write(htmlentitydecode(line))
