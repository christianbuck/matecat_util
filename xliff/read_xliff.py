#!/usr/bin/python

import sys
import xml.etree.ElementTree as ET
import re

''' extract source text from xliff files '''

def peel(s):
    # remove one layer of tags
    re_tag = re.compile(r"^<[^>]+>(?P<inner>.*)<[^>]+>$", re.DOTALL)
    m = re_tag.match(s.strip())
    if m:
        return m.groupdict()['inner'].strip()
    else:
        return s

def remove_ns(s):
    # in: <ns0:x id="7534" /><ns0:g id="7535">
    # out: <x id="7534" /><g id="7535">
    re_ns = re.compile(r'<[^ >]*[:](\w+[ />])')
    return re_ns.sub("<\g<1>",s)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('xliff', help='xliff filename')
    args = parser.parse_args(sys.argv[1:])

    tree = ET.parse(args.xliff)
    root = tree.getroot()

    prefix = '{urn:oasis:names:tc:xliff:document:1.2}'
    for tu in root.iter(prefix + 'trans-unit'):
        if 'translate' in tu.attrib and tu.attrib['translate'] == 'no':
            continue
        for src in tu.iter(prefix + 'source'):
            if (src.text and src.text.strip()) or (src.tail and src.tail.strip()):
                src_text = ET.tostring(src, encoding='utf-8')
                print remove_ns(peel(src_text))
