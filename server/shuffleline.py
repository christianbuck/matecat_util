#!/usr/bin/python -u
import sys
from random import shuffle

cache = []

def output(cache):
    shuffle(cache)
    linenr, line = cache.pop()
    line = list(line)
    #shuffle(line)
    line = "".join(line)
    sys.stderr.write("line: %s\n"%(line))
    print line

for linenr, line in enumerate(sys.stdin):
    line = line.strip()
    if not line:
        break
    sys.stderr.write("adding: %s\n" %(line))
    cache.append( (linenr, line) )
    if len(cache) >= 3:
        output(cache)

sys.stderr.write("end reached, emptying buffer\n")
while(cache):
    output(cache)
