#!/usr/bin/env python

import sys
import StringIO
from lxml import etree as ET

def make_tag(tag, tag_id, attrib=None):
    if attrib:
        attribs = " ".join(["%s=\"%s\"" %(key, val) for key, val in attrib.items()])
        return "<%s_%s %s>" %(tag, tag_id, attribs)
    return "<%s_%s>" %(tag, tag_id)

def annotate_line(line):
    tagstack = []
    annotated_text = []
    tag_id = 0
    parser = ET.iterparse(line, events=("start", "end"))
    for event, elem in parser:
        if event == "start":
            tagstack.append( (elem.tag, tag_id, elem.attrib) )
            tag_id += 1
            print 'start_xml:', ET.tostring(elem)
            print 'start', elem
            if elem.text:
                for token in elem.text.split():
                    annotated_text.append((token, list(make_tag(*tag) for tag in tagstack[1:])))
                print 'text:', elem.text
                print 'tail:', elem.tail
        else:
            print 'end', elem
            print 'end_xml:', ET.tostring(elem)
            assert tagstack[-1][0] == elem.tag
            tagstack.pop()
            if elem.tail:
                for token in elem.tail.split():
                    annotated_text.append((token, list(make_tag(*tag) for tag in tagstack[1:])))
            if elem.text:
                print 'text:', elem.text
            else:
                print


        print 'stack', tagstack
    print annotated_text
    return parser.root[0]

def wrap_segment(line):
    return "<seg>%s</seg>" %line

def anno(tree, stack):
    stack.append( (tree.tag, tree.attrib) )
    if tree.text and tree.text.strip():
        print tree.text, stack
    for child in tree:
        anno(child, stack)
    stack.pop()
    if tree.tail and tree.tail.strip():
        print tree.tail, stack

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

    for line in sys.stdin:
        line = line.strip()
        print 'parsing:', line
        tree = ET.parse(StringIO.StringIO(wrap_segment(line)))
        words = []
        annotated_words = []
        for word, tagstack in anno_iter(tree.getroot(),[]):
            #print len(words), word, tagstack
            annotated_words.append("%s|%s|%s" %(len(words), word, "".join(tagstack)))
            if word.strip():
                words.append(word)
        print '#'.join(annotated_words), " ".join(words)
