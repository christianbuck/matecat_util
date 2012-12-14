#!/usr/bin/env python

import sys
from HTMLParser import HTMLParser
from collections import defaultdict

class TagTypes():
    CONTAINS_NONEMPTY_TEXT = 0     # ex: <a>data</a>
    CONTAINS_EMPTY_TEXT = 1        # ex: <a></a>
    SELF_CONTAINED = 2             # ex: <a/>
    # two additional types to handle broken markup:
    OPENED_BUT_UNCLOSED = 3        # ex: <a>
    CLOSED_BUT_UNOPENED = 4        # ex: </a>

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

    def process(self, line):
        self.reset()
        self.feed(line)
        sys.stderr.write("starting second pass. tag_types: %s\n" %(self.tag_types))
        self.start_second_pass()
        self.feed(line)
        assert not self.stack
        return self.annotated_data, self.tokens

    def handle_starttag(self, tag, attrs):
        self.tag_idx += 1
        self.stack.append( (tag, attrs, self.tag_idx) )
        if self.first_pass:
            # initially assume that tag is properly closed but contains no text
            self.tag_types[self.tag_idx] = (tag, TagTypes.CONTAINS_EMPTY_TEXT)
        else:
            assert self.tag_idx in self.tag_types
            assert self.tag_types[self.tag_idx][0] == tag
            if self.tag_types[self.tag_idx][1] == TagTypes.OPENED_BUT_UNCLOSED:
                self.annotated_data[len(self.tokens)].append(
                    (tag, attrs, self.tag_idx, TagTypes.OPENED_BUT_UNCLOSED) )
                self.stack.pop()
            elif self.tag_types[self.tag_idx][1] == TagTypes.CONTAINS_EMPTY_TEXT:
                self.annotated_data[len(self.tokens)].append(
                    (tag, attrs, self.tag_idx, TagTypes.CONTAINS_EMPTY_TEXT) )
                # pop stack in handle_endtag

    def handle_data(self, data):
        # all tags on the stack potentially contain text
        if not data.strip():
            return
        if self.first_pass:
            for t,a,i in self.stack:
                self.tag_types[i] = (t, TagTypes.CONTAINS_NONEMPTY_TEXT)
        else:
            for token in data.strip().split():
                self.tokens.append(token)
                for t,a,i in self.stack:
                    assert self.tag_types[i] == (t, TagTypes.CONTAINS_NONEMPTY_TEXT)
                    self.annotated_data[len(self.tokens)].append(
                        (t, a, i, TagTypes.CONTAINS_NONEMPTY_TEXT) )
                self.token_idx += 1
        assert len(self.tokens) == self.token_idx

    def handle_startendtag(self, tag, attrs):
        self.tag_idx += 1
        if self.first_pass:
            # no need to put this on the stack
            self.tag_types[self.tag_idx] = (tag, TagTypes.SELF_CONTAINED)
        else:
            assert self.tag_types[self.tag_idx] == (tag, TagTypes.SELF_CONTAINED)
            self.annotated_data[self.token_idx].append(
                (tag, attrs, self.tag_idx, TagTypes.SELF_CONTAINED) )

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
                  self.tag_types[self.tag_idx] = (tag,
                                                  TagTypes.CLOSED_BUT_UNOPENED)
            else:
                assert self.stack
                assert self.stack[-1][0] == tag
                t,a,i = self.stack.pop()
                assert self.tag_types[i][0] == tag
                assert self.tag_types[i][1] in [TagTypes.CONTAINS_EMPTY_TEXT,
                                             TagTypes.CONTAINS_NONEMPTY_TEXT]
        else:
            # in second pass opened to unclosed tags are not pushed to the stack
            # thus we either have the closed-but-upopened case or the standard
            # case of correct markup
            if not self.stack or self.stack[-1][0] != tag:
                self.tag_idx += 1
                self.annotated_data[self.token_idx].append(
                    (tag, {}, self.tag_idx, TagTypes.CLOSED_BUT_UNOPENED))
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
