#!/usr/bin/env python

import sys
import StringIO
from lxml import etree as ET
from xml.sax.saxutils import escape, unescape
from xml.sax.saxutils import quoteattr

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
            yield word, stack[1:]
    else:
        yield '', stack[1:]
    for child in tree:
        for res in anno_iter(child, stack, tagid):
            yield res
    stack.pop()
    if tree.tail and tree.tail.strip():
        for word in tree.tail.split():
            yield word, stack[1:]

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-noescape', action='store_true', help='don\'t escape <&> and quotations')
    parser.add_argument('-nosource', action='store_true', help='don\'t include src attribute')
    args = parser.parse_args(sys.argv[1:])

    for line in sys.stdin:
        line = line.strip()
        #print 'parsing:', line
        tree = ET.parse(StringIO.StringIO(wrap_segment(line)))
        words = []
        annotated_words = []
        for word, tagstack in anno_iter(tree.getroot(),[]):
            #print len(words), word, tagstack
            if tagstack:
                annotated_words.append("%s#%s" %(len(words), "".join(tagstack)))
            if word.strip():
                words.append(word)
        annotated_words = '||'.join(annotated_words)
        #print annotated_words, " ".join(words)

        if not args.noescape:
            escaped_annotated_words = escape(annotated_words, {"'":"&apos;", '"':"&quot;"})
            assert annotated_words == unescape(escaped_annotated_words, {"&apos;":"'", "&quot;":'"'})
            annotated_words = escaped_annotated_words

        if annotated_words:
            src = escape(" ".join(words), {"'":"&apos;", '"':"&quot;"})
            if args.nosource:
                print "<passthrough tag=\"%s\"/>%s" %(annotated_words, src)
            else:
                print "<passthrough tag=\"%s\" src=\"%s\"/>%s" %(annotated_words, src, src)
        else:
            print line
