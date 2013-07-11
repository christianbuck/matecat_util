#!/usr/bin/python

import urllib
import sys

for line in sys.stdin:
    print urllib.quote(line)
