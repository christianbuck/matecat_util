#!/usr/bin/env python

import sys
from xml.etree.cElementTree import iterparse
from xml.etree import cElementTree as ET
import StringIO
import xml.sax

from lxml import etree

def annotate_line(line):
    tagstack = []
    text = []
    parser = iterparse(line, events=("start", "end"))
    for event, elem in parser:
        if event == "start":
            tagstack.append(elem.tag)
            print 'start_xml:', ET.tostring(elem)
            print 'start', elem
            if elem.text:
                for token in elem.text.split():
                    text.append((token, list(tag for tag in tagstack[1:])))
                print 'text:', elem.text
                print 'tail:', elem.tail
        else:
            print 'end', elem
            print 'end_xml:', ET.tostring(elem)
            if elem.tail:
                for token in elem.tail.split():
                    text.append((token, list(tag for tag in tagstack[1:])))
            if elem.text:
                print 'text:', elem.text
            assert tagstack[-1] == elem.tag
            tagstack.pop()
        print 'stack', tagstack
    print text
    return parser.root[0]

def wrap_segment(line):
    return "<seg>%s</seg>" %line

if __name__ == "__main__":
    #import argparse
    #parser = argparse.ArgumentParser()
    #parser.add_argument('infile', action='store', help="input file")
    #parser.add_argument('n', action='store', type=int, help="number argument")
    #parser.add_argument('-b', action='store_true', dest='binary',
    #                    help='binary option', default=False)
    #args = parser.parse_args(sys.argv[1:])

    for line in sys.stdin:
        annotate_line(StringIO.StringIO(wrap_segment(line)))
    #for event, elem in iterparse(sys.stdin, events=("start", "end")):
    #    if event == "start":
    #        print 'start', elem
    #        tagstack.append(elem.tag)
    #    else:
    #        print 'end', elem
    #        print 'text:', elem.text
    #        assert tagstack[-1] == elem.tag
    #        tagstack.pop()
    #    print 'stack', tagstack
