#!/usr/bin/env python

from Levenshtein import *

class Levenshtein(object):
    OPS = ["I", "D", "S", "K"]
    INS, DEL, SUB, KEEP = OPS

    def __init__(self, s1, s2):
        self.s1 = s1
        self.s2 = s2
        self.Q = self._matrix()

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
            else:
                assert False, repr(ops[-1])
        ops.reverse()
        return ops

class TokenTracker(object):
    def _escape(self, s):
        # from tokenizer.perl:
        #$text =~ s/\&/\&amp;/g;   # escape escape
        #$text =~ s/\|/\&#124;/g;  # factor separator
        #$text =~ s/\</\&lt;/g;    # xml
        #$text =~ s/\>/\&gt;/g;    # xml
        #$text =~ s/\'/\&apos;/g;  # xml
        #$text =~ s/\"/\&quot;/g;  # xml
        #$text =~ s/\[/\&#91;/g;   # syntax non-terminal
        #$text =~ s/\]/\&#93;/g;   # syntax non-terminal
        s = s.replace('&','&amp;')
        s = s.replace('|','&#124;')
        s = s.replace('<','&lt;')
        s = s.replace('>','&gt;')
        s = s.replace('\'','&apos;')
        s = s.replace('"','&quot;')
        s = s.replace('[','&#91;')
        s = s.replace(']','&#93;')
        return s

    def _unescape(self, s):
        s = s.replace('&amp;','&')
        s = s.replace('&#124;','|')
        s = s.replace('&lt;','<')
        s = s.replace('&gt;','>')
        s = s.replace('&apos;','\'')
        s = s.replace('&quot;','"')
        s = s.replace('&#91;','[')
        s = s.replace('&#93;',']')
        return s

    def _differs_only_by_space(self, s1, s2):
        pass

    def tokenize(self, s, spaces=(" "), escape=False):
        assert s == s.strip(), "spaces surrounding string not allowed"
        if escape:
            s = self._escape(s)
        spans = [[0,0]]
        for i,c in enumerate(s):
            if c in spaces:
                spans.append([i+1,i+1])
            else:
                spans[-1][1] = i
        #tokens = [s[span[0]:span[1]+1] for span in spans]
        #print spans
        #print tokens
        return spans

    def _check_spans(self, s, spans):
        for start, end in spans:
            assert start == None or start < len(s)
            assert end == None or end < len(s)

    def track_detok(self, a, b, spans=None, verbose=False, check_escape=False):
        """ input:
            a: string AFTER tokenization
            b: string BEFORE tokenization
            spans: list of pairs of indices in a

            returns: list of pairs of indices in b
                that correspond to the input spans
        """
        if verbose:
            print "tokenized:   ", a.encode("utf-8")
            print "untokenized: ", b.encode("utf-8")

        if spans == None:
            spans = self.tokenize(a.encode("utf-8"))
        if a == b:
            return spans

        if check_escape:
            a_unescaped = self._unescape(a)
            b_unescaped = self._unescape(b)
            if a_unescaped != a and b_unescaped == b: # escaping happened in this step
                spans = self.track_detok(a,a_unescaped,
                                         spans=spans,
                                         verbose=verbose)
                a = a_unescaped

        #lev = Levenshtein(b, a)
        #editops = lev.editops()
        #print editops
        #a_idx = 0
        #b_idx = 0
        #alignment = []
        #for op in editops:
            #if verbose:
                #print (a_idx, a[a_idx], b_idx, b[b_idx], op)
            #if op == Levenshtein.KEEP:
                #assert a[a_idx] == b[b_idx], (a_idx, a[a_idx], b_idx, b[b_idx], op)
                #alignment.append((a_idx, b_idx))
                #a_idx += 1
                #b_idx += 1
            #elif op == Levenshtein.DEL: # deleted in b
                #a_idx += 1
            #elif op == Levenshtein.INS:
                #b_idx += 1
            #elif op == Levenshtein.SUB:
                #assert a[a_idx] != b[b_idx], (a_idx, a[a_idx], b_idx, b[b_idx], op)
                #alignment.append((a_idx, b_idx))
                #a_idx += 1
                #b_idx += 1
            #else:
                #assert False, repr(op)

        # use https://github.com/ztane/python-Levenshtein
        # opcodes('a funnny joke', 'a fun yoke')
        # -> [('equal', 0, 5, 0, 5), ('delete', 5, 8, 5, 5), ('equal', 8, 9, 5, 6), ('replace', 9, 10, 6, 7), ('equal', 10, 13, 7, 10)]
        alignment = []
        a = a.encode("utf-8")
        b = b.encode("utf-8")
        for operation in opcodes(a,b):
          if operation[0] == 'equal' or operation[0] == 'replace':
            offset_a = operation[1]
            offset_b = operation[3]
            # prefer del-match-ins over replace-replace (both are 2 edits)
	    if operation[2]-operation[1] == 2 and (a[operation[1]] == b[operation[3]+1] or a[operation[1]+1] == b[operation[3]]):
	      if a[operation[1]] == b[operation[3]+1]:
                alignment.append((offset_a,offset_b+1))   
              else:
                alignment.append((offset_a+1,offset_b))
            # default
            else: 
              for i in range(operation[2]-operation[1]):
                alignment.append((offset_a+i,offset_b+i))

        alignment = dict(alignment)
        new_spans = []
        for start, end in spans:
            mapped_idx = []
            for a_idx in range(start, end+1):
                if a_idx in alignment:
                    mapped_idx.append(alignment[a_idx])
            if mapped_idx:
                new_spans.append((min(mapped_idx), max(mapped_idx)))
            else:
                new_spans.append([None, None])
        if verbose:
            print "old spans: ", spans
            print "old tokens"
            for start, end in spans:
                print '|', a[start:end+1],
            print "|"
            print "new spans: ", new_spans
            print "new tokens"
            for start, end in new_spans:
                if start == None and end == None:
                    print '|', "DELETED",
                else:
                    print '|', b[start:end+1],
            print "|"
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
