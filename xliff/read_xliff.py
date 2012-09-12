#!/usr/bin/python

import sys
import xml.etree.ElementTree as ET

''' extract source text from xliff files '''

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
            if src.text and src.text.strip():
                print src.text.encode('utf-8')
