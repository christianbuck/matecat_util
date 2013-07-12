#!/usr/bin/python

import sys
import xml.etree.ElementTree as ET
import re

''' extract source text from xliff files '''

def peel(s, tag = None):
    # remove one layer of tags
    re_tag = re.compile(r"^\s*<[^>]+>(?P<inner>.*)<[^>]+>\s*$", re.DOTALL)
    if tag != None:
        re_tag = re.compile("^\s*<%s[^>]+>(?P<inner>.*)</%s[^>]*>\s*$" %(tag, tag), re.DOTALL)
    m = re_tag.match(s)
    if m:
        return m.groupdict()['inner'].strip()
    else:
        return s

def peel_all(s, tags = None):
    if tags == None:
        tags = [None]
    old_s = None
    while old_s != s or s == '':
        old_s = s
        for tag in tags:
            s = peel(s)
    return s

def strip_tags(s, tag):
    re_tag = re.compile("</?%s(\s[^>]*)?>" %(tag))
    return re_tag.sub('',s)

def remove_ns(s):
    # in: <ns0:x id="7534" /><ns0:g id="7535">
    # out: <x id="7534" /><g id="7535">
    re_ns = re.compile(r'<(/?)[^ >]*[:](\w+[ />])')
    return re_ns.sub("<\g<1>\g<2>",s)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('xliff', help='xliff filename')
    parser.add_argument('-clean', action='store_true', help='remove g and x tags')
    args = parser.parse_args(sys.argv[1:])

    sys.stderr.write("processing %s\n" %(args.xliff))
    tree = ET.parse(args.xliff)
    root = tree.getroot()

    # urn:oasis:names:tc:xliff:document:1.2
    prefix = '{urn:oasis:names:tc:xliff:document:1.2}'
    for tu in root.iter(prefix + 'trans-unit'):
        if 'translate' in tu.attrib and tu.attrib['translate'] == 'no':
            continue
        for src in tu.iter(prefix + 'source'):
            src_text = ET.tostring(src, encoding='utf-8')
            src_text = remove_ns(src_text)
            src_text = peel(src_text, 'source')
            if args.clean:
                src_text = strip_tags(src_text, 'g')
                src_text = strip_tags(src_text, 'x')
            if src_text.strip():
                print src_text
