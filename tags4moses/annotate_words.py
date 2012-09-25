#!/usr/bin/env python

import sys
import StringIO
from xml.sax.saxutils import escape, unescape

# import chain from http://lxml.de/tutorial.html
try:
  from lxml import etree as ET
except ImportError:
  try:
    # Python 2.5
    import xml.etree.cElementTree as ET
    print("running with cElementTree on Python 2.5+")
  except ImportError:
    try:
      # Python 2.5
      import xml.etree.ElementTree as ET
      print("running with ElementTree on Python 2.5+")
    except ImportError:
      try:
        # normal cElementTree install
        import cElementTree as ET
        print("running with cElementTree")
      except ImportError:
        try:
          # normal ElementTree install
          import elementtree.ElementTree as ET
          print("running with ElementTree")
        except ImportError:
          print("Failed to import ElementTree from any known place")

def make_attrib(name, val):
    quot = '"'
    if '"' in val:
        quot = "'"
    return "%s=%s%s%s" %(name, quot, val, quot)

def make_tag(tag, tag_id, attrib=None):
    if attrib:
        attribs = " ".join([make_attrib(key, val) for key, val in attrib.items()])
        return "<%s_%s %s>" %(tag, tag_id, attribs)
    return "<%s_%s>" %(tag, tag_id)

def wrap_segment(line):
    return "<seg>%s</seg>" %line

def anno_iter(tree, stack=None, tagid=None):
    if stack == None:
        stack = []
    if tagid == None:
        tagid = [0] # we need a mutable type here
    stack.append( make_tag(tree.tag, tagid[0], tree.attrib) )
    tagid[0] += 1
    #if type(tree) == ET._Comment:
    #    yield str(tree)
    if tree.text and tree.text.strip():
        for word in tree.text.split():
            yield word, stack[1:], 0
    else:
        if tree.text:
            yield '', stack[1:], 2
        else:
            yield '', stack[1:], 1
    for child in tree:
        for res in anno_iter(child, stack, tagid):
            yield res
    stack.pop()
    if tree.tail and tree.tail.strip():
        for word in tree.tail.split():
            yield word, stack[1:], 0

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-noescape', action='store_true', help='don\'t escape <,&,> and quotations')
    parser.add_argument('-nosource', action='store_true', help='don\'t include src attribute')
    parser.add_argument('-sourceonly', action='store_true', help='text only, remove markup')
    args = parser.parse_args(sys.argv[1:])

    for line in sys.stdin:
        line = line.strip()
        #print 'parsing:', line
        tree = ET.parse(StringIO.StringIO(wrap_segment(line)))
        words = []
        annotated_words = []
        for word, tagstack, self_contained in anno_iter(tree.getroot(),[]):
            for tag in tagstack:
                annotated_words.append("%s#%s#%s" %(len(words), tag, self_contained))
            assert self_contained or word.strip()
            if word.strip():
                words.append(word)
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

