#!/usr/bin/env python
import sys
import subprocess
import os
import re

#Example output from mgiza:
"""# Sentence pair (1) source length 1 target length 1 alignment score : 9.99e-15
#Musharraf
#NULL ({ }) Moucharraf ({ 1 })
"""


class OnlineMGiza(object):

    def __init__(self, commandline):
        self.cmd = commandline.split()
        self.devnull = open(os.devnull, "w")
        self.proc = None
        self.__restart()

    def __restart(self):
        if self.proc:
            self.proc.communicate("EOA\n")
        self.proc = subprocess.Popen(self.cmd,
                                     stdin=subprocess.PIPE,
                                     stdout=subprocess.PIPE,
                                     stderr=self.devnull)

    def __process(self, source_target_pair):
        self.proc.stdin.write(source_target_pair)
        self.proc.stdin.flush()
        pair_info = self.proc.stdout.readline().strip()
        target = self.proc.stdout.readline().strip()
        source_aligned = self.proc.stdout.readline().strip()
        print "pair info:" ,pair_info
        print "target: " ,target
        print "source_aligned: ", source_aligned
        self.__restart()
        return pair_info, target, source_aligned

    def align(self, src, tgt):
        unicode_pair = u"<src>%s</src><trg>%s</trg>\n" %(src, tgt)
        unicode_pair = unicode_pair.encode("utf-8")
        print unicode_pair
        pair_info, target, source_aligned = self.__process(unicode_pair)
        alignment = self._parse_alignment(target, source_aligned)
        #alignment.sort()
        print alignment
        #assert len(alignment) == len(tgt.split()), \
        #    "alignment length: %s target length: %s\n" \
        #    %(len(alignment), len(tgt.split()))
        return alignment

    def _parse_alignment(self, target, aligned_source):
        """ return a list of source indices, one for each target word. """
        # Example "# NULL ({ }) ({ ({ 1 2 }) x ({ }) ) ({ 3 })"
        re_align = re.compile(r'\S+ \({ ((?:\d+ )*)}\)')
        aligned_words = re_align.findall(aligned_source)
        aligned_words = [map(int, i.strip().split()) for i in aligned_words]
        print aligned_words
        target = target.split()
        #assert len(aligned_words) == len(target) + 1 # target words + NULL
        #aligned_words = aligned_words[1:] # ignore NULL alignments
        alignment = [0] * len(target)
        for aj, js in enumerate(aligned_words):
            for j in js:
                assert j <= len(target)
                assert j > 0
                alignment[j-1] = aj
                #alignment[j]
                #alignment.append( (j, aj) ) # or the other way around?

        return alignment

    def close(self):
        self.proc.stdin.write("EOA")
        self.proc.stdin.flush()
        self.proc.terminate()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('omgiza', help='path of online-MGiza++, including arguments')
    args = parser.parse_args(sys.argv[1:])

    giza = OnlineMGiza(args.omgiza)
    giza.align("Moucharraf", "Musharraf")
