#!/usr/bin/env python

class Levenshtein(object):
    OPS = ["I", "D", "S", "K"]
    INS, DEL, SUB, KEEP = OPS

    def __init__(self, s1, s2):
        self.s1 = s1
        self.s2 = s2
        self.Q = self._matrix()
    #
    #def __substitution_cost(c1, c2):
    #    if c1 != c2 and not c1.strip()

    def _matrix(self):
        Q = [[None]*(len(self.s1)+1) for i in range(len(self.s2)+1)]
        for i in range(len(self.s1)+1):
            Q[0][i] = (i, self.INS)
        for j in range(len(self.s2)+1):
            Q[j][0] = (j, self.DEL)
        for i, c1 in enumerate(self.s1):
            for j, c2 in enumerate(self.s2):
                # compute options for Q[j+1][i+1]
                insert_cost  = Q[j+1][i][0] + 1
                delete_cost  = Q[j][i+1][0] + 1
                replace_cost = Q[j][i][0] + (c1 != c2) # or keep
                cost = [insert_cost, delete_cost, replace_cost]
                best_cost = min(cost)
                best_op = self.OPS[cost.index(best_cost)]
                if best_op == Levenshtein.SUB and c1 == c2:
                    best_op = Levenshtein.KEEP

                Q[j+1][i+1] = (best_cost, best_op)
        self._dist = Q[-1][-1][0]
        return Q

    def __printQ(self, Q):
        for linenr, line in enumerate(Q):
            print linenr, line

    def dist(self):
        return self._dist

    def editops(self):
        """ how to turn s2 into s1 """
        ops = []
        i, j = len(self.Q[0])-1 , len(self.Q)-1
        while i > 0 or j > 0:
            ops.append(self.Q[j][i][1])
            if ops[-1] == self.INS:
                i -= 1
            elif ops[-1] == self.DEL:
                j -= 1
            elif ops[-1] == self.SUB or ops[-1] == self.KEEP:
                i -= 1
                j -= 1
        ops.reverse()
        return ops

class TokenTracker(object):
    def tokenize(self, s, spaces=(" ")):
        assert s == s.strip(), "spaces surrounding string not allowed"
        spans = [[0,0]]
        for i,c in enumerate(s):
            if c in spaces:
                spans.append([i+1,i+1])
            else:
                spans[-1][1] = i
        tokens = [s[span[0]:span[1]+1] for span in spans]
        print spans
        print tokens
        return spans

    def _check_spans(self, s, spans):
        for start, end in spans:
            assert start == None or start < len(s)
            assert end == None or end < len(s)

    def track_detok(self, a, b, spans=None, verbose=False):
        if spans == None:
            spans = self.tokenize(a)[0]
        lev = Levenshtein(b, a)
        editops = lev.editops()
        print editops
        a_idx = 0
        b_idx = 0
        alignment = []
        for op in editops:
            if verbose:
                print a_idx, a[a_idx], b_idx, b[b_idx], op
            if op == Levenshtein.KEEP:
                assert a[a_idx] == b[b_idx]
                alignment.append((a_idx, b_idx))
                a_idx += 1
                b_idx += 1
            elif op == Levenshtein.DEL: # deleted in b
                #alignment.append((a_idx, b_idx))
                a_idx += 1
            elif op == Levenshtein.SUB:
                assert a[a_idx] != b[b_idx]
                alignment.append((a_idx, b_idx))
                a_idx += 1
                b_idx += 1
        print alignment
        alignment = dict(alignment)
        new_spans = []
        print spans
        for start, end in spans:
            mapped_idx = []
            for a_idx in range(start, end+1):
                if a_idx in alignment:
                    mapped_idx.append(alignment[a_idx])
            if mapped_idx:
                new_spans.append((min(mapped_idx), max(mapped_idx)))
            else:
                new_spans.append([None, None])
        #print new_spans
        if verbose:
            for start, end in new_spans:
                if start == None and end == None:
                    print "DELETED"
                else:
                    print b[start:end+1]
        return new_spans



if __name__ == "__main__":
    import sys
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('string1')
    parser.add_argument('string2')
    parser.add_argument('-reverse', action='store_true')
    parser.add_argument('-uncased', action='store_true')
    parser.add_argument('-verbose', action='store_true')
    args = parser.parse_args(sys.argv[1:])

    print "S1:", args.string1
    print "S2:", args.string2
    s1, s2 = args.string1, args.string2
    if args.reverse:
        s1, s2 = s2, s1
    if args.uncased:
        s1 = s1.lower()
        s2 = s2.lower()
    #tokenize(s1)
    #tokenize(s2)
    st = TokenTracker()
    st.track_detok(s1, s2, verbose=args.verbose)
