#!/usr/bin/env python

import sys
import codecs
import locale

# sometimes

n_lines, n_fixed = 0, 0
if __name__ == "__main__":
    sys.stdin = codecs.getreader(locale.getpreferredencoding())(sys.stdin)
    sys.stdout = codecs.getwriter(locale.getpreferredencoding())(sys.stdout)
    for linenr, line in enumerate(sys.stdin):
        n_lines += 1
        try:
            fixed_line = unicode(line.encode("iso-8859-1"), 'utf-8')
            sys.stdout.write(fixed_line)
            if fixed_line != line:
                n_fixed += 1
        except (UnicodeDecodeError, UnicodeEncodeError):
            sys.stdout.write(line)

    if n_lines > 0:
        sys.stderr.write("fixed %s of %s lines (%0.2f%%).\n"
                         %(n_fixed, n_lines, 100.*n_fixed/n_lines))
