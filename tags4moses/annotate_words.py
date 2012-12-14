#!/usr/bin/env python

import sys
from xml.sax.saxutils import escape, unescape
from resilientparser import ResilientParser

def make_attrib(name, val):
    # change quotation character from " to ' if " appears within the value
    quot = '"'
    if '"' in val:
        quot = "'"
    return "%s=%s%s%s" %(name, quot, val, quot)

def make_tag(tag, tag_id, attrib=None):
    if attrib:
        attribs = " ".join([make_attrib(key, val) for key, val in attrib])
        return "<%s_%s %s>" %(tag, tag_id, attribs)
    return "<%s_%s>" %(tag, tag_id)

def parse_line(line):
  parser = ResilientParser()
  annotation, tokens = parser.process(line)
  tokens.insert(0, None)
  for idx, token in enumerate(tokens):
    yield idx, token, annotation[idx]

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-noescape', action='store_true', help='don\'t escape <,&,> and quotations')
    parser.add_argument('-nosource', action='store_true', help='don\'t include src attribute')
    parser.add_argument('-sourceonly', action='store_true', help='text only, remove markup')
    args = parser.parse_args(sys.argv[1:])

    for line in sys.stdin:
        line = line.strip()
        words = []
        annotated_words = []
        for idx, word, annotation in parse_line(line):
          for tag, attr, tag_idx, tag_type in annotation:
            t = make_tag(tag, tag_idx, attr)
            annotated_words.append("%s#%s#%s" %(idx, t, tag_type))
          if word != None and word.strip():
            words.append(word)
          assert idx == len(words)
        annotated_words = '||'.join(annotated_words)

        if not args.noescape:
            escaped_annotated_words = escape(annotated_words, {"'":"&apos;", '"':"&quot;"})
            assert annotated_words == unescape(escaped_annotated_words, {"&apos;":"'", "&quot;":'"'})
            annotated_words = escaped_annotated_words

        src = escape(" ".join(words), {"'":"&apos;", '"':"&quot;"})
        src = src.encode('utf-8')
        if not args.sourceonly:
            if args.nosource:
                print "<passthrough tag=\"%s\"/>%s" %(annotated_words, src)
            else:
                print "<passthrough tag=\"%s\" src=\"%s\"/>%s" %(annotated_words, src, src)
        else:
            print src
