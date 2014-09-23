#!/usr/bin/env python
import sys
import subprocess
import os
import re
import time
import multiprocessing
import string
import random
def id_generator(size=6, chars=string.ascii_uppercase + string.digits):
  return ''.join(random.choice(chars) for _ in range(size))

#Example output from mgiza:
"""# Sentence pair (1) source length 1 target length 1 alignment score : 9.99e-15
#Musharraf
#NULL ({ }) Moucharraf ({ 1 })
"""

class OnlineMGiza(object):

    def __init__(self, commandline, logfile):
        self.cmd = commandline.split()
        self.devnull = open(os.devnull, "w")
        self.proc = None
        self.ready = False
        self.logfile_prefix = logfile
        self.logfile = logfile
        print "trying to match sourcevocabularyfile against %s" % commandline
        result = re.match(r".+sourcevocabularyfile (\S+) .+",commandline)
        if result:
          print "-> %s" % result.group(1)
        self.src_vcb = self.__load_dictionary(result.group(1)) if result else None
        result = re.match(r".+targetvocabularyfile (\S+) .+",commandline)
        self.tgt_vcb = self.__load_dictionary(result.group(1)) if result else None
        sys.stdout.flush()
        self.cache = dict()
        self.__restart()

    # cache handling
    def __load_dictionary(self, filename):
        print "load dictionary %s " % filename
        dictionary = set()
        for line in open(filename,"r"):
          item = line.split()
          dictionary.add(item[1])
        return dictionary
 
    def __check_in_cache(self, source, target):
      key = self.__cache_key(source,target)
      return self.cache.get(key)

    def __store_in_cache(self, source, target, alignment):
      key = self.__cache_key(source,target)
      print "mgiza: store in cache: %s" % key.encode('utf-8')
      self.cache[ key ] = alignment

    def __cache_key(self, source, target):
      if self.src_vcb and self.tgt_vcb:
        return "".join([self.__junk_unknown(source,self.src_vcb)," *+++* ",self.__junk_unknown(target,self.tgt_vcb)])
      else:
        return "".join([source," *+++* ",target])

    def __junk_unknown(self, line, dictionary):
      return " ".join([ word if word in dictionary else "***" for word in line.split()])

    # start the mgiza binary process
    def __restart(self):
        if self.proc:
            self.proc.communicate("EOA\n")
        if self.logfile_prefix:
            self.logfile = "%s.%s" % (self.logfile_prefix, id_generator())
            err = open(self.logfile,"wb")
        else:
            err = self.devnull
        self.ready = False
        self.proc = subprocess.Popen(self.cmd,
                                     stdin=subprocess.PIPE,
                                     stdout=subprocess.PIPE,
                                     stderr=err)

    def __check_if_ready( self ):
        if self.ready:
          return True
        if not self.logfile:
          return True
        log = open(self.logfile,"r")
        for line in log:
          if line.find("Please enter new sentence pair") >= 0:
            print "mgiza: ready"
            self.ready = True
            return True
        print "mgiza: not ready"
        return False
        
    def __process(self, source_target_pair, ret):
        print source_target_pair
        try:
          self.proc.stdin.write(source_target_pair)
          self.proc.stdin.flush()
          ret["pair_info"] = self.proc.stdout.readline().strip()
          ret["target"] = self.proc.stdout.readline().strip()
          ret["source_aligned"] = self.proc.stdout.readline().strip()
        except:
          ret["pair_info"] = ""
          ret["target"] = ""
          ret["source_aligned"] = "there was an error"
        print "pair info:", ret["pair_info"]
        print "target: ", ret["target"]
        print "source_aligned: ", ret["source_aligned"]

    def align(self, src, tgt):
        alignment = self.__check_in_cache(src, tgt)
        if alignment is not None:
          print "mgiza cache: %s " % alignment
          return alignment
        print "mgiza: not in cache"

        ready = self.__check_if_ready()
        if ready:
          unicode_pair = u"<src>%s</src><trg>%s</trg>\n" %(src, tgt)
          unicode_pair = unicode_pair.encode("utf-8")
          print unicode_pair

          # prepare process to call mgiza with timout
          manager = multiprocessing.Manager()
          ret = manager.dict()
          p = multiprocessing.Process(target=self.__process, args=(unicode_pair,ret))
          p.start()
          p.join(2) # wait for two seconds max

          # success
          if not p.is_alive():
            self.ready = True
            alignment = self._parse_alignment(ret["target"], ret["source_aligned"])
            print alignment
            print "len: %d / %d" % (len(alignment),len(tgt.split()))
            if len(alignment) == len(tgt.split()):
              self.__store_in_cache(src, tgt, alignment)
              return alignment

          # failure
          print "mgiza crashed"
          p.terminate()
          p.join()
          self.proc.kill()
          self.proc = None
          self.__restart()
        # dummy response
        alignment = [0] * len(tgt.split())
        print alignment
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

    giza = OnlineMGiza(args.omgiza,None)
    giza.align("Moucharraf", "Musharraf")
