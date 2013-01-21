#!/usr/bin/env python

import sys
import gzip, io
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
    def __init__(self, s2tf, t2sf):

        self.epsilon = 0.000001
        s2t_model = []
        t2s_model = []
        s_voc = {}
        t_voc = {}
        s_inv_voc = {}
        t_inv_voc = {}
        s_last_idx = 0
        t_last_idx = 0
        for tword, sword, pr in imap(str.split, s2tf):
	    s_exists = sword in s_voc
	    t_exists = tword in t_voc
            if s_exists == False :
                s_voc[sword] = s_last_idx
                s_inv_voc[s_last_idx] = sword
		s2t_model.append({})
		s_last_idx = s_last_idx + 1
            sidx = s_voc[sword]

            if t_exists == False :
	        t_voc[tword] = t_last_idx
                t_inv_voc[t_last_idx] = tword
		t2s_model.append({})
		t_last_idx = t_last_idx + 1
            tidx = t_voc[tword]

            s2t_model[sidx][tidx] = float(pr)
##            sys.stdout.write("sword:%s tword:%s s2t_model[sidx][tidx]:%s ->  sidx:%s tidx:%s  ->  s_exists:%s t_exists:%s\n" %(sword, tword, s2t_model[sidx][tidx], sidx, tidx, s_exists, t_exists))

        for sword, tword, pr in imap(str.split, t2sf):
            s_exists = sword in s_voc
            t_exists = tword in t_voc
            if t_exists == False :
                t_voc[tword] = t_last_idx
                t_inv_voc[t_last_idx] = tword
		t2s_model.append({})
		t_last_idx = t_last_idx + 1
            tidx = t_voc[tword]

            if s_exists == False :
                s_voc[sword] = s_last_idx
                s_inv_voc[s_last_idx] = sword
		s_lastidx = s_last_idx + 1
            sidx = s_voc[sword]
 
            t2s_model[tidx][sidx] = float(pr)
##            sys.stdout.write("tword:%s sword:%s t2s_model[tidx][sidx]:%s ->  tidx:%s sidx:%s  ->  t_exists:%s s_exists:%s\n" %(tword, sword, t2s_model[tidx][sidx], tidx, sidx, t_exists, s_exists))
        self.s_voc = s_voc
        self.t_voc = t_voc
        self.s_inv_voc = s_inv_voc
        self.t_inv_voc = t_inv_voc
        self.s2t_model = s2t_model
        self.t2s_model = t2s_model

    def get_voc(self, side):
        if side == 'source':
            return self.s_voc
        if side == 'target':
            return self.t_voc

    def align(self, src, tgt, phrase_alignment=None):
        Q = self.update(src, tgt, phrase_alignment)
	self.__printQ(Q,True)
        a = self.best_alignment(Q)
        a.reverse()
        return a

    def init_q(self, J, I, alignment):
        Q = [[None]*(I+1) for s in range(J)]
        for src_idx, tgt_idx in alignment:
            assert len(tgt_idx)>0
            for j in tgt_idx:
                if len(src_idx) == 0: # unaligned
                    for i in range(I+1):
                        Q[j][i] = 0
                else:
                    for i in range(I):
                        Q[j][i] = 0 # mark all words impossible
                    for i in src_idx:
                        Q[j][i] = None    # mark aligned words possible
                    Q[j][I] = None # mark all words impossible
        return Q

    def t2s_score(self, tidx, sidx):
        tmp = self.t2s_model[tidx]
        if sidx in tmp:
#            sys.stdout.write("MATCH: w_t:%s w_s:%s pr:%s\n" %(tidx, sidx, self.t2s_model[tidx][sidx]))
            return self.t2s_model[tidx][sidx]
        else:
            return self.epsilon

    def s2t_score(self, sidx, tidx):
        tmp = self.s2t_model[sidx]
        if tidx in tmp:
#            sys.stdout.write("MATCH: w_s:%s w_t:%s pr:%s\n" %(sidx, tidx, self.s2t_model[sidx][tidx]))
            return self.s2t_model[sidx][tidx]
        else:
            return self.epsilon

    def update(self, src, tgt, phrase_alignment):
        I = len(src)
        J = len(tgt)
        Q = [[None]*(I+1) for s in tgt]
        if phrase_alignment:
            Q = self.init_q(J, I, phrase_alignment)
        for j in range(J):
            w_t = tgt[j]
            for i in range(I+1):  # a_j
                if not Q[j][i] == None:
                    continue
                w_s = 0
                if i < I:
                    w_s = src[i]
		else:
                    w_s = self.s_voc['NULL']

                lex_prob = self.s2t_score(w_s, w_t)
#                lex_prob = self.t2s_score(w_t, w_s)
#                lex_prob = self.s2t_score(w_s, w_t) * self.t2s_score(w_t, w_s)
                Q[j][i] = lex_prob
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

    def best_alignment(self, Q, verbose=False): # backtrace
        J = len(Q)
        I = len(Q[0]) - 1
        alignment = []

        for j in range(J):
            best_idx = I
            best = Q[j][I]
            for i in range(I):
                if best == None or Q[j][i] > best:
                    best = Q[j][i];
                    best_idx = i

	    if best_idx == I:
	        best_idx = -1
            if verbose:
                print j, best_idx, "->", Q[j][best_idx]
            a_j = best_idx
            alignment.append((j, a_j))

        return alignment

def smart_open(filename):
    if filename.endswith('.gz'):
        return io.BufferedReader(gzip.open(filename))
    return open(filename)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
##    parser.add_argument('sourcevoc', action='store', help="source vocabulary")
##    parser.add_argument('targetvoc', action='store', help="target vocabulary")
    parser.add_argument('s2tlex', action='store', help="source-target lexicon")
    parser.add_argument('t2slex', action='store', help="target-source lexicon")
    parser.add_argument('-lower', action='store_true', help='lowercase input')
    parser.add_argument('-verbose', action='store_true', help='more output')
    args = parser.parse_args(sys.argv[1:])

    IBM1 = IBM1Aligner(smart_open(args.s2tlex),smart_open(args.t2slex))
    src_voc = Vocabulary(IBM1.get_voc('source'))
    tgt_voc = Vocabulary(IBM1.get_voc('target'))

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
#        sys.stdout.write("\nSRC TXT:%s\n and VOC:%s\n" %(src_txt,src))
#        sys.stdout.write("\nTGT TXT:%s\n and VOC:%s\n" %(tgt_txt,tgt))

        # compute a target-to-source alignment:
        # each target word is aligned to none or one source words
        alignment = IBM1.align(src, tgt, phrase_alignment=align)
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
