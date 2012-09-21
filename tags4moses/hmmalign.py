#!/usr/bin/env python

import sys
import gzip, io
from collections import defaultdict
from itertools import imap

from moparser import MosesOutputParser

class Vocabulary(object):
    def __init__(self, f):
        self.voc, self.inv_voc = self.read_vocab(f)

    def read_vocab(self, f):
        voc = {}
        inv_voc = {}
        for idx, word, count in imap(str.split, f):
            idx = int(idx)
            voc[word] = idx
            inv_voc[idx] = word
        return voc, inv_voc

    def map_sentence(self, snt):
        snt = snt.strip().split()
        return [self.voc.get(w,0) for w in snt]

class LexTrans(object):
    def __init__(self, f):
        self.lex_probs = defaultdict(dict)
        for src, tgt, cnt, p in imap(str.split, f):
            self.lex_probs[int(src)][int(tgt)] = float(p)   # p(tgt|src)

    def sum_transtable(self):
        for src in self.lex_probs:
            print src, sum(self.lex_probs[src].values())

    def __contains__(self, src):
        return src in self.lex_probs

    def get(self, src, tgt, default=0.0):
        assert src in self.lex_probs, "no probs for src word %s\n" %(src)
        return self.lex_probs[src].get(tgt, 0.0)

class HMMAligner(object):
    def __init__(self, hmm_file, lex_file):
        self.lex_probs = LexTrans(lex_file)
        self.read_hmm(hmm_file)

    def read_hmm(self, f):
        # read a file that look like this
        # 3 -2:182.773; -1:1106.93; 0:664.036; 1:44.329; 2:26.9507;
        self.transition_probs = defaultdict(dict)
        for linenr, line in enumerate(f):
            line = line.rstrip().replace(';','').split()
            tgt_len = int(line[0])
            for jump, s in imap(lambda x:x.split(':'), line[1:]):
                self.transition_probs[tgt_len][int(jump)] = float(s)

        for tgt_len, probs in self.transition_probs.iteritems():
            s_sum = sum(probs.values())
            for jump, s in probs.iteritems():
                probs[jump] /= s_sum

    def align(self, src, tgt, pnull=.4): # todo: exchange source and target
        Q = self.viterbi( src, tgt, pnull)
        a = self.viterbi_alignment(Q)
        a.reverse()
        return a

    def init_q(self, src_len, tgt_len, alignment):
        Q = [[None]*tgt_len*2 for s in range(src_len)]
        for src_idx, tgt_idx in alignment:
            assert len(tgt_idx)>0
            if len(src_idx) == 0: # unaligned
                pass


    def viterbi(self, src, tgt, pnull=0.4):
        I = len(src)
        J = len(tgt)
        Q = [[None]*I*2 for s in tgt]
        jump_probs = self.transition_probs[I]
        for j in range(J):
            w_t = tgt[j]
            for i in range(2*I):  # a_j
                w_s = 0
                if i < I:
                    w_s = src[i]
                assert w_s in self.lex_probs
                lex_prob = self.lex_probs.get(w_s, w_t, default=0.0)
                if j == 0: # first word
                    jump_prob = 1.0
                    Q[j][i] = (jump_prob * lex_prob, -1)
                else:
                    best = None
                    q_max = max(p for p,back in Q[j-1])
                    for k in range(2*I): # a_{j-1}
                        jump_prob = 0.0
                        if i < I:
                            if k < I:
                                jump = i-k
                            else:
                                jump = i-k+I
                            jump_prob = jump_probs.get(-jump, 0.)
                        else: # align to nullword
                            if k==i or k == i-I:
                                jump_prob = pnull
                        prev_prob = Q[j-1][k][0]
                        if q_max > 0:
                            prev_prob /= q_max
                        prob = jump_prob * prev_prob
                        if best == None or best[1] < prob:
                            best = (k, prob)
                    Q[j][i] = (best[1]*lex_prob, best[0])
        #self.printQ(Q, transpose=True)
        return Q

    def printQ(self, Q, transpose=False):
        if transpose:
            for j in range(len(Q)):
                for i in range(len(Q[0])):
                    print "Q(%s,%s)=%s" %(j,i,str(Q[j][i]))
        else:
            for i in range(len(Q[0])):
                for j in range(len(Q)):
                    print "Q(%s,%s)=%s" %(j,i,str(Q[j][i]))

    def viterbi_alignment(self, Q, verbose=False): # backtrace
        j = len(Q)-1
        alignment = []
        best = None
        best_idx = None
        for i in range(len(Q[j])):
            if best == None or Q[j][i][0] > best[0]:
                best = Q[j][i];
                best_idx = i
        while j>=0:
            if verbose:
                print j+1, best_idx+1, "->", Q[j][best_idx][1]
            a_j = best_idx
            if best_idx >= len(Q[j])/2:
                a_j = -1
            alignment.append((j, a_j))

            best_idx = Q[j][best_idx][1]
            j -= 1
        return alignment

def smart_open(filename):
    if filename.endswith('.gz'):
        return io.BufferedReader(gzip.open(filename))
    return open(filename)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('hmmfile', action='store', help="HMM transition probs from GIZA++")
    parser.add_argument('lexprobs', action='store', help="translation probs")
    parser.add_argument('sourcevoc', action='store', help="source vocabulary")
    parser.add_argument('targetvoc', action='store', help="target vocabulary")
    parser.add_argument('-pnull', action='store', type=float, help="jump probability to/from NULL word (default: 0.4)", default=0.4)
    #parser.add_argument('-verbose', action='store_true', help='more output', default=False)
    args = parser.parse_args(sys.argv[1:])

    hmm = HMMAligner(smart_open(args.hmmfile), smart_open(args.lexprobs))
    src_voc = Vocabulary(smart_open(args.sourcevoc))
    tgt_voc = Vocabulary(smart_open(args.targetvoc))

    parser = MosesOutputParser()
    for line in sys.stdin:
        line = line.strip()
        src, tgt, align, tag = parser.parse(line)

        print src
        print tgt

        src = src_voc.map_sentence(src)
        tgt = tgt_voc.map_sentence(tgt)

        print src
        print tgt

        # compute a target-to-source alignment:
        # each target word is aligned to none or one source words
        #alignment = hmm.align(tgt, src)
        alignment = hmm.align(src, tgt)
        print alignment


    sys.exit()

    tgt = "4908 2053 4443 72".split()     # Musharafs letzter Akt ?
    src = "1580 12 5651 3533 75".split()  # Musharf 's last Act ?

    src = map(int,"3308 6 767 2946 103 3 6552 1580 28 8938 468 12 1260 1294 7 1652 9 122 5 2183 4".split())
    tgt = map(int,"7 30 10421 722 2 37 5 148 7020 2 38 7690 1943 9 638 5 2739 491 1085 6 9 10288 12029 4".split())

    src = "desperate to hold onto power , Pervez Musharraf has discarded Pakistan &apos;s constitutional framework and declared a state of emergency ."
    tgt = "in dem verzweifelten Versuch , an der Macht festzuhalten , hat Pervez Musharraf den Rahmen der pakistanischen Verfassung verlassen und den Notstand ausgerufen ."


    print src
    print tgt
