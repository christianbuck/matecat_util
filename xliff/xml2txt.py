#!/usr/bin/python

import sys
import xml.etree.ElementTree as ET
import re

''' extract all text from xml files '''

def peel(s):
    # remove one layer of tags
    re_tag = re.compile(r"^<[^>]+>(?P<inner>.*)<[^>]+>$", re.DOTALL)
    m = re_tag.match(s.strip())
    if m:
        return m.groupdict()['inner'].strip()

def get_text(tree):
    if (tree.text and tree.text.strip()) or (tree.tail and tree.tail.strip()):
        text = ET.tostring(tree, encoding='utf-8').strip()
        yield peel(text)
    else:
        for child in tree:
            for text in  get_text(child):
                yield text

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('xml', help='xml filename')
    args = parser.parse_args(sys.argv[1:])

    tree = ET.parse(args.xml)
    root = tree.getroot()

    for text in get_text(root):
        print text
