#!/usr/bin/env python

import sys
import gzip, io
import re
from collections import defaultdict
from itertools import imap

from moparser import MosesOutputParser

class Vocabulary(object):
    def __init__(self, voc):
        self.voc = voc

    def map_sentence(self, snt, lowercase=False):
        snt = snt.strip().split()
        if lowercase:
            snt = snt.lower()
        return [self.voc.get(w,0) for w in snt]

class IBM1Aligner(object):
    epsilon = 0.000001

    def __init__(self, s2tf, t2sf):
        self.s2t_model = defaultdict(lambda: dict())
        for tword, sword, pr in imap(str.split, s2tf): # t s p(t|s)
            self.s2t_model[sword][tword] = float(pr)

        self.t2s_model = defaultdict(lambda: dict()) # s t p(s|t)
        for sword, tword, pr in imap(str.split, t2sf):
            self.t2s_model[tword][sword] = float(pr)

    def align(self, src, tgt, phrase_alignment=None):
        I = len(src)
        J = len(tgt)
        Q = self.update(src, tgt, I, J, phrase_alignment)
#        self.__printQ(Q,True)
        a = self.best_alignment(Q, I, J)
        return a

    def update(self, src, tgt, I, J, phrase_alignment):
        Q = [[None]*(I+1) for s in tgt] # None means possible but unknown
                                        # I+1 to allow alignment to NULL word
        if phrase_alignment: # mark some positions impossible
            Q = self.init_q(J, I, phrase_alignment)
        for j in range(J):
            w_t = tgt[j]
            for i in range(I+1):  # a_j
                if not Q[j][i] == None:
                    continue
                w_s = 'NULL'
                if i < I:
                    w_s = src[i]

                lex_prob = self.s2t_prob(w_s, w_t)
                Q[j][i] = lex_prob
        return Q

    def init_q(self, J, I, alignment):
        """ generate cost-matrix and mark impossible positions """
        Q = [[None]*(I+1) for s in range(J)]
        for src_idx, tgt_idx in alignment:
            assert len(tgt_idx)>0
            for j in tgt_idx:
                for i in range(I+1):
                    Q[j][i] = 0 # mark all words impossible
                if len(src_idx) == 0: # unaligned
                    Q[j][I] = None
                else:
                    for i in src_idx:
                        Q[j][i] = None    # mark aligned words possible
        return Q

    def best_alignment(self, Q, I, J, verbose=False): # backtrace
        """ just picking the best word for every target index """
        alignment = []

        for j in range(J):
            best_idx = I
            best = None
            for i in range(I+1):
                if best == None or Q[j][i] > best:
                    best = Q[j][i];
                    best_idx = i

            if best_idx == I:
                best_idx = -1 # aligned to NULL word means unaligned
            if verbose:
                sys.stderr.write("%s %s -> %s\n" %(j, best_idx, Q[j][best_idx]))
            a_j = best_idx
            alignment.append((j, a_j))

        return alignment

    def _get_prob(self, probs, key1, key2, min_val=0.0):
        """ get value from a dict-of-dicts structure (probs).
            Ignores missing values and returns at least min_val """
        if not key1 in probs:
            return min_val
        return max(min_val, probs[key1].get(key2, 0.0))

    def t2s_prob(self, t, s):
        """ lexical probability of translating target word t as s """
        return self._get_prob(self.t2s_model, t, s, self.epsilon)

    def s2t_prob(self, s, t):
        """ lexical probability of translating source word s as t """
        return self._get_prob(self.s2t_model, s, t, self.epsilon)

    def __printQ(self, Q, transpose=False):
        """ mostly for debugging """
        if transpose:
            for j in range(len(Q)):
                for i in range(len(Q[0])):
                    print "Q(%s,%s)=%s" %(j,i,str(Q[j][i]))
        else:
            for i in range(len(Q[0])):
                for j in range(len(Q)):
                    print "Q(%s,%s)=%s" %(j,i,str(Q[j][i]))

def smart_open(filename):
    if filename.endswith('.gz'):
        return io.BufferedReader(gzip.open(filename))
    return open(filename)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('s2tlex', action='store', help="source-target lexicon")
    parser.add_argument('t2slex', action='store', help="target-source lexicon")
    parser.add_argument('-lower', action='store_true', help='lowercase input')
    parser.add_argument('-printXmlWordAlignment', action='store_true', help='print word alignment in passthough xml tag')
    parser.add_argument('-printXmlPhraseAlignment', action='store_true', help='print phrase alignment in passthough xml tag')
    parser.add_argument('-verbose', action='store_true', help='more output')
    args = parser.parse_args(sys.argv[1:])

    IBM1 = IBM1Aligner(smart_open(args.s2tlex),smart_open(args.t2slex))

    parser = MosesOutputParser()
    for line in iter(sys.stdin.readline, ''):
        line = line.strip()
        if not line: continue
        src_txt, tgt_txt, palign, tag, markup = parser.parse(line)

        # compute a target-to-source alignment:
        # each target word is aligned to none or one source words
        alignment = IBM1.align(src_txt.split(), tgt_txt.split(), phrase_alignment=palign)
        alignment = dict(alignment)

        # add phrase and/or word-alignment to markup string
        if args.printXmlPhraseAlignment:
            phrasealignmentstr = ""
            for i in range(len(palign)):
                if i > 0:
                    phrasealignmentstr = "%s , " %(phrasealignmentstr)
                phrasealignmentstr = "%s[ %s , %s ]" \
                    %(phrasealignmentstr,str(palign[i][0]),str(palign[i][1]))
            phrasealignmentstr = re.sub(' ','',phrasealignmentstr)
            if args.verbose:
                sys.stderr.write("\nsrc: %s\ntgt: %s\nphrasealignmentstr: %s\n"
                                    % (src_txt, tgt_txt, phrasealignmentstr))
            markup = "%s<passthrough phrase_alignment=\"[%s]\"/>" \
                                    % (markup, phrasealignmentstr)

        if args.printXmlWordAlignment:
            wordalignmentstr = ""
            for i in range(len(alignment)):
                if alignment[i] != -1:
                    if wordalignmentstr:
                        wordalignmentstr = "%s , " %(wordalignmentstr)
                    wordalignmentstr = "%s[ [%d] , [%d] ]" %(wordalignmentstr,alignment[i],i)
            wordalignmentstr = re.sub(' ','',wordalignmentstr)
            if args.verbose:
                sys.stderr.write("\nsrc: %s\ntgt: %s\nwordalignmentstr: %s\n"
                                    % (src_txt, tgt_txt, wordalignmentstr))
            markup = "%s<passthrough word_alignment=\"[%s]\"/>" \
                                    % (markup, wordalignmentstr)

        sys.stdout.write(markup)
        for j, w in enumerate(tgt_txt.rstrip().split()):
            if j>0:
                sys.stdout.write(" ")
            sys.stdout.write("%s |%s|" %(w, alignment[j]))
        sys.stdout.write("\n")
        sys.stdout.flush()

    sys.exit()
