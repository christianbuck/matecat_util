#!/usr/bin/python

import urllib
import sys
import re

re_tag = re.compile(r'(<[^>]+>)')

substitutions = {
    '"' : "#MC_DOUBLEQUOTE#",
    "'" : "#MC_SINGLEQUOTE#",
    '<' : "#MC_LT#",
    '>' : "#MC_GT#"
}

def quote(t, use_mc=True):
    if not use_mc:
        return urllib.quote(t)
    for k,v in substitutions.iteritems():
        t = t.replace(k, v)
    return t

def wrap_tag(t, use_mc=True):
    quoted_tag = quote(t, use_mc)
    template = "<n translation=\"%s\">tag</n>"
    return template %(quoted_tag)

for line in sys.stdin:
    line = re_tag.split(line)
    #print line
    if len(line) > 1:
        for idx in range(1, len(line), 2):
            #print line[idx]
            line[idx] = wrap_tag(line[idx])
            #print line[idx]
    sys.stdout.write("".join(line))
    sys.stdout.flush()
