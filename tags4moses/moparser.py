#!/usr/bin/env python

import re

class MosesOutputParser(object):
    def __init__(self):
        pass

    def parse(self, line):
        src, tag, tgt = self.parse_moses_output(line)
        words, align = self.parse_alignment(tgt)
        return src, words, align, tag

    def parse_moses_output(self, line):
        # <passthrough tag="1#<b_1 id="4">||2#<b_1 id="4"><i_2>||4#<dot_3>" src="Also nested tags work ."/>Geschachtelte Tags |1-2| gehen |3| auch |0| . |4|
        re_src = re.compile(r'^<passthrough [^>]*src="(?P<src>[^"]*)"')
        re_tag = re.compile(r'^<passthrough [^>]*tag="(?P<tag>[^"]*)"')
        re_tgt = re.compile(r'^<passthrough [^>]*>(?P<tgt>.*)$')

        src_match = re_src.match(line)
        assert src_match
        src = src_match.groupdict()['src']

        tag_match = re_tag.match(line)
        assert tag_match
        tag = tag_match.groupdict()['tag']

        tgt_match = re_tgt.match(line)
        assert tgt_match
        tgt = tgt_match.groupdict()['tgt']

        return src, tag, tgt

    def parse_alignment(self, tgt):
        # Geschachtelte Tags |1-2| gehen |3| auch |0| . |4|
        align = []
        words = []
        tgt_start = len(words)
        for w in tgt.split():
            if w[0] == '|' and w[-1] == '|':
                tgt_end = len(words)
                tgt_range = range(tgt_start, tgt_end)

                src_range= []
                if w != '|-1|': # alignment found
                    src_start = int(w[1:-1].split('-')[0])
                    src_end = int(w[1:-1].split('-')[-1])
                    src_range = range(src_start, src_end+1)

                align.append( (src_range, tgt_range) )
                tgt_start = len(words)
            else:
                words.append(w)
        return words, align

if __name__ == "__main__":
    line = '<passthrough tag="1#&lt;b_1 id=&quot;4&quot;&gt;||2#&lt;b_1 id=&quot;4&quot;&gt;&lt;i_2&gt;||4#&lt;dot_3&gt;" src="Also nested tags work ."/>Geschachtelte Tags |1-2| gehen |3-3| auch |0-0| prima |-1| . |4-4|'
    parser = MosesOutputParser()
    src, words, align, tag = parser.parse(line)

    print src
    print words
    print align
    print tag
