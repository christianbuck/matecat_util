#!/usr/bin/env python

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
                replace_cost = Q[j][i][0] + (c1 != c2)
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



if __name__ == "__main__":
    import sys
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('string1')
    parser.add_argument('string2')
    args = parser.parse_args(sys.argv[1:])

    mylev = Levenshtein(args.string1, args.string2)
    print mylev.dist()
    print mylev.editops()
