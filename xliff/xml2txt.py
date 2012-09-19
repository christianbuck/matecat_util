#!/usr/bin/python

import sys
import xml.etree.ElementTree as ET

''' extract source text from xliff files '''

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('xml', help='xml filename')
    args = parser.parse_args(sys.argv[1:])

    tree = ET.parse(args.xml)
    root = tree.getroot()

    for src in root.iter():
        if src.text and src.text.strip():
            src_text = src.text.strip().replace("\n",'NEWLINE')
            print src_text.encode('utf-8')
