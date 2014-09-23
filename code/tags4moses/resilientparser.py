#!/usr/bin/env python

import sys
from HTMLParser import HTMLParser
from collections import defaultdict
import re

# for a start-and-end tag, the space type assigned to the tag is composed by XY, where X is the spacetype of the start tag, and Y is the spacetype of the end tag; or UNDEFINED, if either X or Y is undefined
# for a self-contained tag, the space type assigned to the tag is composed by X, where X is the spacetype of the only tag; or UNDEFINED, if X is undefined

class SpaceTypes():
    UNDEFINED = -1                 # undefined (used for the inner words, but the first, of NONEMPTY tags
    SPACE_NO = 0                   # ex: the<a>data
    SPACE_ONLY_BEFORE = 1          # ex: the <a>data
    SPACE_ONLY_AFTER = 2           # ex: the<a> data
    SPACE_BEFORE_AND_AFTER = 3     # ex: the <a> data
    SPACE_INTERNAL = 100             # ex: <a /> used only for self_contained tags

class TagTypes():
    CONTAINS_NONEMPTY_TEXT = 0     # ex: <a>data</a>
    CONTAINS_EMPTY_TEXT = 1        # ex: <a></a>
    SELF_CONTAINED = 2             # ex: <a/>
    # two additional types to handle broken markup:
    OPENED_BUT_UNCLOSED = 3        # ex: <a>
    CLOSED_BUT_UNOPENED = 4        # ex: </a>
    # extra types for some moses magic
    NOTRANSLATE = 5                # ex: <span class="notranslate"...>xxx</span>
    FORCETRANSLATE = 6             # ex: <span class="forcetranslate"...>xxx</span>

class ResilientParser(HTMLParser):
    def __init__(self):
        #super(HTMLParser,self).__init__()
        HTMLParser.__init__(self) # HTMLParser is oldstyle

    def reset(self):
        HTMLParser.reset(self)
        #super(ResilientParser,self).reset()
        self.stack = []
        self.annotated_data = defaultdict(list)
        self.tokens = []
        self.first_pass = True
        self.tag_types = {}
        self.tag_idx = 0
        self.token_idx = 0

    def start_second_pass(self):
        assert self.first_pass
        for t,a,i in self.stack:
            self.tag_types[i] = (t, TagTypes.OPENED_BUT_UNCLOSED)

        self.tag_idx = 0
        self.stack = []
        assert not self.annotated_data
        assert self.token_idx == 0
        self.first_pass = False

    def fix_annotation(self):
	re_attr = re.compile('(class)')
	re_value = re.compile('(notranslate)')
        for idx, token in enumerate(self.tokens):
	    ann_data = self.annotated_data[idx+1]

	    new_ann_data = []
            for tag in ann_data:
		name = tag[0]
		attrs = tag[1]
		tag_idx = tag[2]
		type = tag[3]
                for attr in attrs:
		    if name == "span" and attr[0] == "class":
			if attr[1] == "notranslate":
                            type = TagTypes.NOTRANSLATE
		        elif attr[1] == "forcetranslate":
                            type = TagTypes.FORCETRANSLATE
		new_ann_data.append( (name, attrs, tag_idx, type) )
            self.annotated_data[idx+1] = new_ann_data	

    def fix_annotation_spaces(self):
        line = self.line
	new_annotated_data = defaultdict(list)

        for idx in self.annotated_data:
            ann_data = self.annotated_data[idx]
            new_ann_data = []
            for tag in ann_data:
                tag_idx = tag[2]

		type = tag[3]
		spacetype_start = SpaceTypes.UNDEFINED
		spacetype_end = SpaceTypes.UNDEFINED
		spacetype_internal = 0
		spacetype = SpaceTypes.UNDEFINED

                cased_tag = self.tag_types[tag_idx][0]

                if type == TagTypes.SELF_CONTAINED :
                        pattern = "<"+cased_tag+"[^>]*(\s+)\/>"
                        if re.search(pattern, line) :
                                spacetype_internal = SpaceTypes.SPACE_INTERNAL

                pattern1 = "([^\s]|^)<"+cased_tag+"[^>]*>([^\s]|$)"
                pattern2 = "(\s)<"+cased_tag+"[^>]*>([^\s]|$)"
                pattern3 = "([^\s]|^)<"+cased_tag+"[^>]*>(\s)"
                pattern4 = "(\s)<"+cased_tag+"[^>]*>(\s)"
		if re.search(pattern1, line) :
		        spacetype_start = SpaceTypes.SPACE_NO
			line = re.sub(pattern1, "\g<1>\g<2>", line, 1)
		elif re.search(pattern2, line) :
			spacetype_start = SpaceTypes.SPACE_ONLY_BEFORE
			line = re.sub(pattern2, "\g<1>\g<2>", line, 1)
		elif re.search(pattern3, line) :
			spacetype_start = SpaceTypes.SPACE_ONLY_AFTER
			line = re.sub(pattern3, "\g<1>\g<2>", line, 1)
		elif re.search(pattern4, line) :
			spacetype_start = SpaceTypes.SPACE_BEFORE_AND_AFTER
			line = re.sub(pattern4, "\g<1>\g<2>", line, 1)
		if spacetype_start != SpaceTypes.UNDEFINED :
			spacetype_start = spacetype_start

		if type == TagTypes.CONTAINS_NONEMPTY_TEXT or type == TagTypes.CONTAINS_EMPTY_TEXT : 
                	pattern1 = "([^\s]|^)<\/"+cased_tag+"[^>]*>([^\s]|$)"
                	pattern2 = "(\s)</"+cased_tag+"[^>]*>([^\s]|$)"
                	pattern3 = "([^\s]|^)</"+cased_tag+"[^>]*>(\s)"
                	pattern4 = "(\s)</"+cased_tag+"[^>]*>(\s)"
                	if re.search(pattern1, line) :
                	        spacetype_end = SpaceTypes.SPACE_NO
			        line = re.sub(pattern1, "\g<1>\g<2>", line, 1)
                	if re.search(pattern2, line) :
                        	spacetype_end = SpaceTypes.SPACE_ONLY_BEFORE
			        line = re.sub(pattern2, "\g<1>\g<2>", line, 1)
                	if re.search(pattern3, line) :
                        	spacetype_end = SpaceTypes.SPACE_ONLY_AFTER
			        line = re.sub(pattern3, "\g<1>\g<2>", line, 1)
                	if re.search(pattern4, line) :
                	        spacetype_end = SpaceTypes.SPACE_BEFORE_AND_AFTER
			        line = re.sub(pattern4, "\g<1>\g<2>", line, 1)
			if spacetype_start == SpaceTypes.UNDEFINED or spacetype_end == SpaceTypes.UNDEFINED:
				spacetype = SpaceTypes.UNDEFINED
			else:
				spacetype = 10*spacetype_start + spacetype_end
		else:
			spacetype = spacetype_start
		spacetype += spacetype_internal

		if idx > 0 :
	            prev_ann_data = new_annotated_data[idx-1]
	            for prev_tag in prev_ann_data:
	                prev_tag_idx = prev_tag[2]
			if tag_idx == prev_tag_idx :
	                    prev_spacetype = prev_tag[4]
			    spacetype = prev_spacetype
	
                new_ann_data.append( (tag[0], tag[1], tag[2], tag[3], spacetype) ) 
            new_annotated_data[idx] = new_ann_data
	self.annotated_data.clear()
        self.annotated_data = new_annotated_data

    def process(self, line):
        self.reset()
	self.line = line
        self.feed(line)
        self.start_second_pass()
        self.feed(line)
        assert not self.stack
        self.fix_annotation()
        self.fix_annotation_spaces()
        return self.annotated_data, self.tokens

    def get_cased_start_tag(self, expected_tag=None):
	re_tag = re.compile('<(?P<tag_name>[^/\s]+)[^>]*>')
        text = self.get_starttag_text()
        if not text:
            assert not expected_tag
        else:
            m = re_tag.match(text)
            assert m
            if expected_tag:
                assert m.group('tag_name').lower() == expected_tag, "found %s but expected %s\n" %(m.group('tag_name'), expected_tag)
            return m.group('tag_name')
        return None

    def handle_starttag(self, tag, attrs):
        cased_tag = self.get_cased_start_tag(tag)

        assert cased_tag != None
        self.tag_idx += 1
        self.stack.append( (cased_tag, attrs, self.tag_idx) )

        if self.first_pass:
            # initially assume that tag is properly closed but contains no text
            self.tag_types[self.tag_idx] = (cased_tag, TagTypes.CONTAINS_EMPTY_TEXT)
        else:
            assert self.tag_idx in self.tag_types
            assert self.tag_types[self.tag_idx][0] == cased_tag
            if self.tag_types[self.tag_idx][1] == TagTypes.OPENED_BUT_UNCLOSED:
                self.annotated_data[len(self.tokens)].append(
                    (cased_tag, attrs, self.tag_idx, TagTypes.OPENED_BUT_UNCLOSED) )
                self.stack.pop()
            elif self.tag_types[self.tag_idx][1] == TagTypes.CONTAINS_EMPTY_TEXT:
                self.annotated_data[len(self.tokens)].append(
                    (cased_tag, attrs, self.tag_idx, TagTypes.CONTAINS_EMPTY_TEXT) )
                # pop stack in handle_endtag

    def handle_data(self, data):
        # all tags on the stack potentially contain text
        if not data.strip():
            return
        if self.first_pass:
            for cased_tag,a,i in self.stack:
                assert i in self.tag_types
                assert cased_tag == self.tag_types[i][0]
                self.tag_types[i] = (cased_tag, TagTypes.CONTAINS_NONEMPTY_TEXT)
        else:
            for token in data.strip().split():
                self.tokens.append(token)
                for cased_tag,a,i in self.stack:
                    assert cased_tag == self.tag_types[i][0]
                    assert self.tag_types[i][1] == TagTypes.CONTAINS_NONEMPTY_TEXT
                    self.annotated_data[len(self.tokens)].append(
                        (cased_tag, a, i, TagTypes.CONTAINS_NONEMPTY_TEXT) )
                self.token_idx += 1
        assert len(self.tokens) == self.token_idx

    def handle_startendtag(self, tag, attrs):
        self.tag_idx += 1
        if self.first_pass:
            # no need to put this on the stack
            cased_tag = self.get_cased_start_tag(tag)
            assert cased_tag != None
            self.tag_types[self.tag_idx] = (cased_tag, TagTypes.SELF_CONTAINED)
        else:
            tag_type = self.tag_types[self.tag_idx][1]
            assert tag_type == TagTypes.SELF_CONTAINED or tag_type == TagTypes.SELF_CONTAINED_WS
            assert self.tag_types[self.tag_idx][0].lower() == tag
            cased_tag = self.tag_types[self.tag_idx][0]
            assert cased_tag != None
            self.annotated_data[self.token_idx].append( (cased_tag, attrs, self.tag_idx, tag_type) )

    def handle_endtag(self, tag):
        if self.first_pass:
            if not self.stack or self.stack[-1][0] != tag:
              # unexpected tag is closing -
              # 1. check if this can be fixed by closing some tags from the stack
              open_tags = [t for t,a,i in self.stack]
              if tag in open_tags:
                    t,a,i = self.stack.pop()
                    while t != tag:
                        self.tag_types[i] = (t, TagTypes.OPENED_BUT_UNCLOSED)
                        t,a,i = self.stack.pop()
              # 2. fix by opening and close immediately
              else:
                  self.tag_idx += 1
                  self.tag_types[self.tag_idx] = (tag, TagTypes.CLOSED_BUT_UNOPENED)
            else:
                assert self.stack
                assert self.stack[-1][0] == tag
                t,a,i = self.stack.pop()
                assert self.tag_types[i][0] == tag
                assert self.tag_types[i][1] in [TagTypes.CONTAINS_EMPTY_TEXT,
                                             TagTypes.CONTAINS_NONEMPTY_TEXT]
	else:
            # in second pass opened to unclosed tags are not pushed to the stack
            # thus we either have the closed-but-unopened case or the standard
            # case of correct markup

	    if not self.stack or self.stack[-1][0] != tag:
                cased_tag = tag
                self.tag_idx += 1
                if self.tag_types[self.tag_idx][1] == TagTypes.CLOSED_BUT_UNOPENED:
                    self.annotated_data[len(self.tokens)].append(
                        (cased_tag, {}, self.tag_idx, TagTypes.CLOSED_BUT_UNOPENED) )

            else:
                assert self.stack
                assert self.stack[-1][0] == tag
                t,a,i = self.stack.pop()
                assert self.tag_types[i][0] == tag


def process_line(line):
    p = ResilientParser()
    print line
    print p.process(line)

if __name__ == "__main__":
    process_line("<a><b></b></a>")
    process_line("<a></b></a>")
    process_line("<a>foo</a></b>")
    process_line("foo<a></b>")
    process_line("<a><b></a></b>")
    process_line("<a><b>foo</a></b>")
    process_line("<a first-attr=1 second-attr=2 attr-wo-value><b>foo</b attr-at-b-close></a attr-at-a-close=1>")
    process_line("<a><b>one</b> <b>two</b> three</a>")
    process_line("a b <empty></empty> c")
    process_line("a b <solo/> c")
    process_line("a b <ctag> c </ctag>")
    process_line("a b <unclosed> c")
    process_line("a b c </unopened>")
    process_line("a b <ctag> <solo-in-ctag/> c </ctag>")
    process_line("a b <solo-before-ctag/> <ctag> c </ctag>")
