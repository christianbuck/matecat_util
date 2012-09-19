#!/usr/bin/env python

import sys
import gzip
from collections import defaultdict
from itertools import imap, izip

def read_hmm(f):
    # read a file that look like this
    # 3 -2:182.773; -1:1106.93; 0:664.036; 1:44.329; 2:26.9507;
    transition_probs = defaultdict(dict)
    for linenr, line in enumerate(f):
        line = line.rstrip().replace(';','').split()
        tgt_len = int(line[0])
        for jump, s in imap(lambda x:x.split(':'), line[1:]):
            transition_probs[tgt_len][int(jump)] = float(s)

    for tgt_len, probs in transition_probs.iteritems():
        s_sum = sum(probs.values())
        for jump, s in probs.iteritems():
            probs[jump] /= s_sum

    return transition_probs

def read_transtable(f):
    trans_probs = defaultdict(dict)
    for src, tgt, cnt, p in imap(str.split, f):
        trans_probs[int(src)][int(tgt)] = float(p)   # p(tgt|src)
    return trans_probs

def sum_transtable(trans_probs):
    for src in trans_probs:
        print src, sum(trans_probs[src].values())

def read_vocab(f):
    voc = {}
    inv_voc = {}
    for idx, word, count in imap(str.split, f):
        idx = int(idx)
        voc[word] = idx
        inv_voc[idx] = word
    return voc, inv_voc

def map_sentence(voc, snt):
    snt = snt.strip().split()
    return [voc.get(w,0) for w in snt]

def viterbi(hmm_probs, trans_probs, src, tgt, pnull=0.4):
    tgt_len = len(tgt)
    Q = [[None]*tgt_len*2 for s in src]
    for j in range(len(src)):
        w_s = src[j]
        for i in range(2*tgt_len):  # a_j
            w_t = 0
            if i < tgt_len:
                w_t = tgt[i]
            assert w_t in trans_probs
            lex_prob = trans_probs[w_t].get(w_s, 0.0)
            if j == 0: # first word
                jump_prob = 1.0
                Q[j][i] = (jump_prob * lex_prob, -1)
            else:
                best = None
                q_max = max(p for p,back in Q[j-1])
                for k in range(2*len(tgt)): # a_{j-1}
                    jump_prob = 0.0
                    if i < tgt_len:
                        if k < tgt_len:
                            jump = i-k
                        else:
                            jump = i-k+tgt_len
                        jump_prob = hmm_probs[tgt_len].get(-jump, 0.)
                    else: # align to nullword
                        if k==i or k == i-tgt_len:
                            jump_prob = pnull
                    prev_prob = Q[j-1][k][0]
                    prob = jump_prob * prev_prob / q_max
                    if best == None or best[1] < prob:
                        best = (k, prob)
                Q[j][i] = (best[1]*lex_prob, best[0])
    printQ(Q)
    return Q

def printQ(Q):
    for i in range(len(Q[0])):
        for j in range(len(Q)):
            print "Q(%s,%s)=%s" %(j,i,str(Q[j][i]))

def viterbi_alignment(Q):
    j = len(Q)-1
    best = None
    best_idx = None
    for i in range(len(Q[j])):
        if best == None or Q[j][i][0] > best[0]:
            best = Q[j][i];
            best_idx = i
    while j>=0:
        print j+1, best_idx+1, "->", Q[j][best_idx][1]
        best_idx = Q[j][best_idx][1]
        #print "Q(%s,%s)=%s" %(j,i,str(Q[j][i]))
        j -= 1

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('hmmfile', action='store', help="HMM transition probs from GIZA++")
    parser.add_argument('lexprobs', action='store', help="translation probs")
    #parser.add_argument('sourcevoc', action='store', help="source vocabulary")
    #parser.add_argument('targetvoc', action='store', help="target vocabulary")
    parser.add_argument('-pnull', action='store', type=float, help="jump probability to/from NULL word (default: 0.4)", default=0.4)
    #parser.add_argument('-verbose', action='store_true', help='more output', default=False)
    args = parser.parse_args(sys.argv[1:])

    hmm_probs = read_hmm(gzip.open(args.hmmfile))
    trans_probs = read_transtable(gzip.open(args.lexprobs))
    #src_voc = read_vocab(open(args.sourcevoc))
    #tgt_voc = read_vocab(open(args.targetvoc))

    #sum_transtable(trans_probs)

    print "loaded lexprops for %s words from %s"  %(len(trans_probs), args.lexprobs)

    tgt = "4908 2053 4443 72".split()     # Musharafs letzter Akt ?
    src = "1580 12 5651 3533 75".split()  # Musharf 's last Act ?

    src = map(int,"3308 6 767 2946 103 3 6552 1580 28 8938 468 12 1260 1294 7 1652 9 122 5 2183 4".split())
    tgt = map(int,"7 30 10421 722 2 37 5 148 7020 2 38 7690 1943 9 638 5 2739 491 1085 6 9 10288 12029 4".split())

    Q = viterbi(hmm_probs, trans_probs, src, tgt)
    viterbi_alignment(Q)
