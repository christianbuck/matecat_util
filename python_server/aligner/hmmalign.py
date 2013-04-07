#!/usr/bin/env python

import sys
import gzip, io
from collections import defaultdict
from itertools import imap

class Vocabulary(object):
    def __init__(self, f):
        self.voc = {}
        self.inv_voc = {}
        self.read_vocab(f)
        self.unknown_word_idx = self.voc.get('UNK', 0)
        #self.unknown_word_idx = 0

    def read_vocab(self, f):
        for idx, word, count in imap(str.split, f):
            idx = int(idx)
            self.voc[word] = idx
            self.inv_voc[idx] = word

    def map_sentence(self, snt, lowercase=False):
        snt = snt.strip().split()
        if lowercase:
            snt = snt.lower()
        return [self.voc.get(w, self.unknown_word_idx) for w in snt]

class LexTrans(object):
    def __init__(self, lexprob_file, min_prob=0.0):
        self.lex_probs = defaultdict(dict)
        for line in imap(str.split, lexprob_file):
            # process both Giza and MGiza formats
            if len(line) == 3:
                tgt, src, p = line
            else:
                assert len(line) == 4
                tgt, src, cnt, p = line
            if float(p) > min_prob:
                self.lex_probs[int(tgt)][int(src)] = float(p)   # p(src|tgt)
        self.__sanitycheck()


    def __contains__(self, src):
        return src in self.lex_probs

    def get(self, src, tgt, default=0.0):
        """ returns p(src|tgt) or default value if prob is not found """
        if src == 1 and tgt == 0: # unknowns should be unaligned
            return 1.0
        if tgt == 1:
            return default
        assert tgt in self.lex_probs, "no probs for tgt word %s\n" %(tgt)
        return self.lex_probs[tgt].get(src, default)

    def __sanitycheck(self, min_tresh=0.9, max_tresh=1.1):
        """ lexprobs[tgt][src] contains p(src|tgt). Summing these over tgt
        should yield about 1 if we didn't prune the model too much. """
        p_sums = defaultdict(float)
        s_words, t_words = set(), set()
        for tgt in self.lex_probs:
            t_words.add(tgt)
            for src in self.lex_probs[tgt]:
                s_words.add(src)
                p_sums[tgt] += self.lex_probs[tgt][src]
        for tgt, psum in p_sums.iteritems():
            if psum < min_tresh or psum > max_tresh:
                sys.stderr.write("Weird prob. tgt:%s, p: %s\n"%(tgt, psum))
        sys.stdout.write("%s source, %s target\n" %(len(s_words), len(t_words)))

class HMMAligner(object):
    def __init__(self, hmm_file, lex_file, min_prob=0.0):
        self.lex_probs = LexTrans(lex_file, min_prob=0.0)
        self.transition_probs = defaultdict(dict)
        if hmm_file is not None:
            self.read_hmm(hmm_file)

    def read_hmm(self, hmm_file):
        # read a file with jump probs that looks like this
        # 3 -2:182.773; -1:1106.93; 0:664.036; 1:44.329; 2:26.9507;
        for linenr, line in enumerate(hmm_file):
            line = line.rstrip().replace(';','').split()
            tgt_len = int(line[0])
            for jump, s in imap(lambda x:x.split(':'), line[1:]):
                self.transition_probs[tgt_len][int(jump)] = float(s)

        for tgt_len, probs in self.transition_probs.iteritems():
            s_sum = sum(probs.values())
            for jump, s in probs.iteritems():
                probs[jump] /= s_sum

    def align(self, src, tgt, pnull=.4, phrase_alignment=None):
        Q = self.viterbi( src, tgt, pnull, phrase_alignment)
        a = self.viterbi_alignment(Q)
        a.reverse()
        return a

    def init_q(self, J, I, alignment):
        Q = [[None]*I*2 for s in range(J)]
        for src_idx, tgt_idx in alignment:
            assert len(tgt_idx)>0
            for j in tgt_idx:
                if len(src_idx) == 0: # unaligned
                    for i in range(I):
                        Q[j][i] = (0.,-1)
                        Q[j][i+I] = (1.,-1)
                else:
                    for i in range(I):
                        Q[j][i] = (0.,-1) # mark all words impossible
                    for i in src_idx:
                        Q[j][i] = None      # mark aligned words possible
        return Q

    def get_jumpprob(self, I, jump):
        """ return probability of jump

            assuming a jump distribution based on sentence length
            if no data is available all jumps have equal probability (1.0)
        """
        if not I in self.transition_probs:
            return 1.0
        return self.transition_probs[I].get(jump, 0.0)


    def viterbi(self, src, tgt, pnull, phrase_alignment):
        # align each source word to exactly one target word (maybe NULL)
        J = len(src)
        I = len(tgt)
        Q = [[None]*I*2 for j in range(J)]
        if phrase_alignment:
            Q = self.init_q(J, I, phrase_alignment)
        for j in range(J): # iterate of source positions
            source_word = src[j]
            for i in range(2*I):  # all possible a_j
                if not Q[j][i] == None: # ignore alignments marked as impossible
                    continue
                target_word = 0 # NULL word means unaligned
                if i < I:
                    target_word = tgt[i]
                lex_prob = self.lex_probs.get(source_word, target_word, default=0.0)
                if j == 0: # first word
                    jump_prob = 1.0
                    Q[j][i] = (jump_prob * lex_prob, -1)
                else:
                    best = None
                    q_max = 1.0 # for numerical stability
                    try:
                        q_max = max(q[0] for q in Q[j-1] if not q==None)
                    except ValueError:
                        pass
                    for k in range(2*I): # a_{j-1}, i' in Och's paper
                        jump_prob = 0.0
                        if i < I:
                            jump = i - (k%I)
                            jump_prob = self.get_jumpprob(I, -jump)
                        else: # align to nullword
                            if k%I == i%I:
                                jump_prob = pnull
                        prev_prob = Q[j-1][k][0]
                        if q_max > 0:
                            prev_prob /= q_max
                        prob = jump_prob * prev_prob
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
            if best_idx >= len(Q[j])/2:
                a_j = -1
            alignment.append((j, a_j))

            best_idx = Q[j][best_idx][1]
            j -= 1
        return alignment

def smart_open(filename):
    if not filename:
        return None
    if filename.endswith('.gz'):
        return io.BufferedReader(gzip.open(filename))
    return open(filename)

class BidirectionalAligner(object):
    def __init__(self, svoc, tvoc, s2t_jump, s2t_lex, t2s_jump, t2s_lex,
                 minp=0.0, pnull=0.4, lower=False, verbose=False):
        self.lower = lower
        self.minp = minp
        self.pnull = pnull
        self.verbose = verbose
        
        self.src_voc = Vocabulary(smart_open(svoc))
        self.tgt_voc = Vocabulary(smart_open(tvoc))
        
        self.s2t_aligner = HMMAligner(smart_open(s2t_jump),
                                      smart_open(s2t_lex), min_prob=minp)
        self.t2s_aligner = HMMAligner(smart_open(t2s_jump),
                                      smart_open(t2s_lex), min_prob=minp)

    def map_source(self, source_txt):
        return self.src_voc.map_sentence(source_txt, self.lower)

    def map_target(self, target_txt):
        return self.tgt_voc.map_sentence(target_txt, self.lower)

    def align_s2t(self, source_txt, target_txt):
        src = self.map_source(source_txt)
        tgt = self.map_target(target_txt)
        align = self.s2t_aligner.align(src, tgt, pnull=self.pnull)
        return align

    def align_t2s(self, source_txt, target_txt):
        src = self.map_source(source_txt)
        tgt = self.map_target(target_txt)
        align = self.t2s_aligner.align(tgt, src, pnull=self.pnull)
        return align

    def symal(self, source_txt, target_txt):
        s_len = len(source_txt.split())
        s2t_align = self.align_s2t(source_txt, target_txt)
        assert len(s2t_align) == s_len

        t_len = len(target_txt.split())
        t2s_align = self.align_t2s(source_txt, target_txt)
        assert len(t2s_align) == t_len


class SymalWrapper(object):
    def __init__(self, symal_cmd):
        import subprocess
        cmd = symal_cmd.split()
        self.proc = subprocess.Popen(cmd, stdin=subprocess.PIPE,
                                          stdout=subprocess.PIPE)

    def process(self, source_txt, target_txt, s2t_align, t2s_align):
        s_len = len(source_txt.split())
        t_len = len(target_txt.split())
        s2t_align = " ".join([str(a+1) for j,a in s2t_align])
        t2s_align = " ".join([str(a+1) for i,a in t2s_align])
        s = u"1\n%d %s  # %s\n%d %s  #%s\n" %(t_len, target_txt, t2s_align,
                                              s_len, source_txt, s2t_align)
        self.proc.stdin.write(s.encode("utf-8"))
        self.proc.stdin.flush()
        result = self.proc.stdout.readline()
        return result.decode("utf-8").rstrip()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('s2t_hmm', action='store', help="HMM transition probs from GIZA++")
    parser.add_argument('s2t_lex', action='store', help="translation probs")
    parser.add_argument('t2s_hmm', action='store', help="HMM transition probs from GIZA++")
    parser.add_argument('t2s_lex', action='store', help="translation probs")
    parser.add_argument('sourcevoc', action='store', help="source vocabulary")
    parser.add_argument('targetvoc', action='store', help="target vocabulary")
    parser.add_argument('source', action='store', help="source sentence")
    parser.add_argument('target', action='store', help="target sentence")
    parser.add_argument('symal', action='store', help="path to symal, including arguments")
    parser.add_argument('-pnull', action='store', type=float, help="jump probability to/from NULL word (default: 0.4)", default=0.4)
    parser.add_argument('-lower', action='store_true', help='lowercase input')
    parser.add_argument('-verbose', action='store_true', help='more output')
    parser.add_argument('-ignore_phrases', action='store_true', help='ignore alignment info from moses')
    parser.add_argument('-minp', help='minimal translation probability, used to prune the model', default=0.0, type=float)
    args = parser.parse_args(sys.argv[1:])

    src = "desperate to hold onto power , Pervez Musharraf has discarded Pakistan &apos;s constitutional framework and declared a state of emergency ."
    tgt = "in dem verzweifelten Versuch , an der Macht festzuhalten , hat Pervez Musharraf den Rahmen der pakistanischen Verfassung verlassen und den Notstand ausgerufen ."

    ba = BidirectionalAligner(args.sourcevoc, args.targetvoc,
                              args.s2t_hmm, args.s2t_lex,
                              args.t2s_hmm, args.t2s_lex,
                              args.minp, args.pnull, args.lower, args.verbose)

    print ba.align_s2t(args.source, args.target)
    print ba.align_t2s(args.source, args.target)
    print ba.symal(args.source, args.target)


    sys.exit()

    hmm = HMMAligner(smart_open(args.hmmfile), smart_open(args.lexprobs), min_prob=args.minp)
    src_voc = Vocabulary(smart_open(args.sourcevoc))
    tgt_voc = Vocabulary(smart_open(args.targetvoc))

    src_txt = args.source
    tgt_txt = args.target
    src = src_voc.map_sentence(src_txt, args.lower)
    tgt = tgt_voc.map_sentence(tgt_txt, args.lower)

    alignment = dict(hmm.align(src, tgt, phrase_alignment=None))

    if args.verbose:
        sys.stderr.write("source: %s\n" %src)
        sys.stderr.write("target: %s\n" %tgt)
        sys.stderr.write("alignment: %s\n" %(str(alignment)))
    for j, w in enumerate(src_txt.rstrip().split()):
        if j>0:
            sys.stdout.write(" ")
        sys.stdout.write("%s |%s|" %(w, alignment[j]))
    sys.stdout.write("\n")

    sys.exit()



    tgt = "4908 2053 4443 72".split()     # Musharafs letzter Akt ?
    src = "1580 12 5651 3533 75".split()  # Musharf 's last Act ?

    src = map(int,"3308 6 767 2946 103 3 6552 1580 28 8938 468 12 1260 1294 7 1652 9 122 5 2183 4".split())
    tgt = map(int,"7 30 10421 722 2 37 5 148 7020 2 38 7690 1943 9 638 5 2739 491 1085 6 9 10288 12029 4".split())

    src = "desperate to hold onto power , Pervez Musharraf has discarded Pakistan &apos;s constitutional framework and declared a state of emergency ."
    tgt = "in dem verzweifelten Versuch , an der Macht festzuhalten , hat Pervez Musharraf den Rahmen der pakistanischen Verfassung verlassen und den Notstand ausgerufen ."


    print src
    print tgt
