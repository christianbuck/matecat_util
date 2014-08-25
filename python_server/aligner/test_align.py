#!/usr/bin/env python

import sys
import mgiza
import symal

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

    #sw = symal.SymalWrapper(args.symal)
    #print sw.process(s, t, s2t_align, t2s_align)
