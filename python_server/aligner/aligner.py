#!/usr/bin/env python

import sys
import mgiza
import symal

class DiagonalAligner(object):
    """ monotonic dummy aligner for testing """

    def align(self, source, target):
        source_words = ['NULL'] + source.strip().split()
        target_words = target.strip().split()
        alignment = []
        for i, w in source_words:
            alignment.append( (i, len(target_words)*i/len(source_words)) )


class BidirectionalAligner(object):
    def __init__(self, s2taligner, t2saligner, symal):
        self.__s2taligner = s2taligner
        self.__t2saligner = t2saligner
        self.__symal = symal

    @property
    def s2t(self):
        return self.__s2taligner

    @property
    def t2s(self):
        return self.__t2saligner

    @property
    def symal(self):
        return self.__symal

    def symmetrize(self, source_txt, target_txt):
        if not source_txt.strip() or not target_txt.strip():
            return ""
        s_len = len(source_txt.split())
        s2t_align = self.align_s2t(source_txt, target_txt)
        assert len(s2t_align) == s_len

        t_len = len(target_txt.split())
        t2s_align = self.align_t2s(source_txt, target_txt)
        assert len(t2s_align) == t_len

        if self.symal_proc == None:
            return s2t_align, t2s_align
        return self.symal_proc.process(source_txt, target_txt,
                                       s2t_align, t2s_align)

    def invert_direction(self, alignment):
        return ( (y,x) for (x,y) in alignment)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('omgiza_src2tgt', help='path of online-MGiza++, including arguments for src-tgt alignment')
    parser.add_argument('omgiza_tgt2src', help='path of online-MGiza++, including arguments for tgt-src alignment')
    parser.add_argument('symal', help='path to symal, including arguments')
    args = parser.parse_args(sys.argv[1:])


    print args.omgiza_src2tgt
    print args.omgiza_tgt2src
    giza_s2t = mgiza.OnlineMGiza(args.omgiza_src2tgt, None)
    giza_t2s = mgiza.OnlineMGiza(args.omgiza_tgt2src, None)

    s = "1 january 1974"
    t = "il 1 gennaio 1974"

    s2t_align = giza_s2t.align(s, t)
    t2s_align = giza_t2s.align(t, s)

    sw = symal.SymalWrapper(args.symal)
    print sw.process(s, t, s2t_align, t2s_align)

    s2t_align = giza_s2t.align(s, t)
    t2s_align = giza_t2s.align(t, s)
