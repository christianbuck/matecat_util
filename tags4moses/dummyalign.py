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

    def map_sentence(self, snt, lowercase=False):
        if lowercase:
            snt = snt.lower()
        snt = snt.strip().split()
        return [self.voc.get(w,0) for w in snt]

class dummyAligner(object):
    def __init__(self):
        pass

    def align(self, src, tgt, phrase_alignment=None):
        Q = self.viterbi( src, tgt, phrase_alignment)
        a = self.viterbi_alignment(Q)
        a.reverse()
        return a

    def init_q(self, J, I, alignment):
        Q = [[None]*I for s in range(J)]
        for src_idx, tgt_idx in alignment:
            assert len(tgt_idx)>0
            for j in tgt_idx:
                if len(src_idx) == 0: # unaligned
                    for i in range(I):
                        Q[j][i] = (0.,-1)
                else:
                    for i in range(I):
                        Q[j][i] = (0.,-1) # mark all words impossible
                    for i in src_idx:
                        Q[j][i] = None      # mark aligned words possible
        return Q


    def viterbi(self, src, tgt, phrase_alignment):
        I = len(src)
        J = len(tgt)
        Q = [[None]*I for s in tgt]
        if phrase_alignment:
            Q = self.init_q(J, I, phrase_alignment)
        for j in range(J):
            w_t = tgt[j]
            for i in range(I):  # a_j
                if not Q[j][i] == None:
                    continue
                w_s = 0
                if i < I:
                    w_s = src[i]
                lex_prob = 1.0
                if j == 0: # first word
                    Q[j][i] = (lex_prob, -1)
                else:
                    best = None
                    q_max = 1.0
                    try:
                        q_max = max(q[0] for q in Q[j-1] if not q==None)
                    except ValueError:
                        pass
                    for k in range(I): # a_{j-1}
                        prev_prob = Q[j-1][k][0]
			if q_max > 0:
                            prev_prob /= q_max
                        prob = prev_prob
                        if best == None or best[1] < prob:
                            best = (k, prob)
                    Q[j][i] = (best[1]*lex_prob, best[0])
        return Q

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
    parser.add_argument('sourcevoc', action='store', help="source vocabulary")
    parser.add_argument('targetvoc', action='store', help="target vocabulary")
    parser.add_argument('-lower', action='store_true', help='lowercase input')
    parser.add_argument('-verbose', action='store_true', help='more output')
    args = parser.parse_args(sys.argv[1:])

    dummy = dummyAligner()
    src_voc = Vocabulary(smart_open(args.sourcevoc))
    tgt_voc = Vocabulary(smart_open(args.targetvoc))

    parser = MosesOutputParser()
    for line in iter(sys.stdin.readline, ''):
        line = line.strip()
        if not line:
            print line
            continue
        src_txt, tgt_txt, align, tag, markup = parser.parse(line)

        if args.verbose:
	    phrasealignmentstr = ""
	    for i in range(len(align)):
		phrasealignmentstr = "%s %s-%s" %(phrasealignmentstr,str(align[i][0]),str(align[i][1]))
	    phrasealignmentstr = "src: %s\ntgt: %s\nphrase-alignment: %s\n" % (src_txt, tgt_txt, phrasealignmentstr)
            sys.stderr.write(phrasealignmentstr)
        src = src_voc.map_sentence(src_txt, args.lower)
        tgt = tgt_voc.map_sentence(tgt_txt, args.lower)

        # compute a target-to-source alignment:
        # each target word is aligned to none or one source words
        alignment = dummy.align(src, tgt, phrase_alignment=align)
        alignment = dict(alignment)

        if args.verbose:
	    wordalignmentstr = ""
            for i in range(len(alignment)):
		if alignment[i] != -1:
                    wordalignmentstr = "%s %d-%d" %(wordalignmentstr,alignment[i],i)
            wordalignmentstr = "src: %s\ntgt: %s\nword-alignment: %s\n" % (src_txt, tgt_txt, wordalignmentstr)
            sys.stderr.write(wordalignmentstr)

        sys.stdout.write(markup)
        for j, w in enumerate(tgt_txt.rstrip().split()):
            if j>0:
                sys.stdout.write(" ")
            sys.stdout.write("%s |%s|" %(w, alignment[j]))
        sys.stdout.write("\n")
        sys.stdout.flush()

    sys.exit()



    tgt = "4908 2053 4443 72".split()     # Musharafs letzter Akt ?
    src = "1580 12 5651 3533 75".split()  # Musharf 's last Act ?

    src = map(int,"3308 6 767 2946 103 3 6552 1580 28 8938 468 12 1260 1294 7 1652 9 122 5 2183 4".split())
    tgt = map(int,"7 30 10421 722 2 37 5 148 7020 2 38 7690 1943 9 638 5 2739 491 1085 6 9 10288 12029 4".split())

    src = "desperate to hold onto power , Pervez Musharraf has discarded Pakistan &apos;s constitutional framework and declared a state of emergency ."
    tgt = "in dem verzweifelten Versuch , an der Macht festzuhalten , hat Pervez Musharraf den Rahmen der pakistanischen Verfassung verlassen und den Notstand ausgerufen ."


    sys.stdout.write("%s\n" %(src))
    sys.stdout.write("%s\n" %(trg))
    sys.stdout.flush()
##    print src
##    print tgt
