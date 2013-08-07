#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys, logging, os
import codecs, subprocess, select, re
import random
from collections import defaultdict
from itertools import imap

from ConfigParser import SafeConfigParser

logging.basicConfig(level=logging.INFO)

def append_to_file(fn, output):
        """
        Write output to file named fn.
        """
        f = open(fn, 'a')
        f.write(output)
        f.close()

def write_to_file(fn, output):
        """
        Write output to file named fn.
        """
        f = open(fn, 'w')
        f.write(output)
        f.close()

def read_file(fn):
        """
        Read a list of sentences from a file.
        """
        try:
                return [line.strip() for line in open(fn)]
        except IOError:
                sys.stderr.write("Could not open file "+fn+"\n")
                sys.exit()

class Aligner_Dummy:
        """
        Handles constrained search with external scripts.
        """
        def __init__(self, parser):
		self.parser = parser
                self.tmpdir = parser.get('env', 'tmp')

        def align(self, source="", target="", correction="", moses_translation_options=""):
		alignment = []
                return alignment

	
class Aligner_Constrained_Search:
        """
        Handles constrained search with external scripts.
        """
        def __init__(self, parser):
                self.parser = parser
		self.translation_option_extractor = parser.get('tools', 'aligner_options_extractor_path')
		self.aligner = parser.get('tools', 'aligner_constrained_search_path')
                self.tmpdir = parser.get('env', 'tmp')

	def align(self, source="", target="", correction="", moses_translation_options=""):
                logging.info("SEARCHER correction:"+correction)

                # extract translation options from Moses output
                extractor = subprocess.Popen([self.translation_option_extractor], stdin=subprocess.PIPE, stdout=subprocess.PIPE, shell=False)
                logging.info("EXTRACTOR_CALL: "+str(self.translation_option_extractor))
                options, err = extractor.communicate(moses_translation_options)
                logging.debug("EXTRACTOR_OUT: "+options.strip())
                logging.info("EXTRACTOR_ERR: "+str(err))

                # write reference and translation options to temporary files
		rr = str(random.randint(0,1000000))
                crt_file = self.tmpdir+"/_crt"+str(os.getpid())+"_"+rr
                write_to_file(crt_file, correction+'\n')
                opt_file = self.tmpdir+"/_opt"+str(os.getpid())+"_"+rr
                write_to_file(opt_file, options)

                # call constrained search script
                logging.info("SEARCHER_CALL: "+str(self.aligner+" --trans "+opt_file+" --txt "+crt_file))
                aligner = subprocess.Popen([self.aligner, "--trans", opt_file, "--txt", crt_file], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                alignment, err = aligner.communicate()
                logging.info("SEARCHER_OUT: "+alignment.strip())
                logging.info("SEARCHER_ERR: "+str(err))

                # remove temporary files
                os.remove(crt_file), os.remove(opt_file)
                return alignment.strip()

class Aligner_onlineGIZA:
        """
        Handles constrained search with external scripts.
        """
        def __init__(self, parser):
                self.parser = parser
                self.s2tcfg = parser.get('annotation', 'src-trg-gizacfg')
                self.t2scfg = parser.get('annotation', 'trg-src-gizacfg')
                try:
                        parser.get('annotation', 'sym-align-type')
                except:
                        parser.set('annotation', 'sym-align-type', '-a=intersection -d=no -b=no -f=no')
                try:
                        parser.get('annotation', 'giza-options')
                except:
                        parser.set('annotation', 'giza-options', '-m1 1 -m2 0 -m3 0 -m4 0 -m5 0 -mh 0 -restart 1')
                try:
                        self.path = parser.get('tools', 'mgiza_path')
                except:
                        self.path = None

                self.symtype = parser.get('annotation', 'sym-align-type')
                self.gizaoptions = parser.get('annotation', 'giza-options')
                self.tmpdir = parser.get('env', 'tmp')


                self.parameters_s2t = self.s2tcfg+" " + self.gizaoptions + " -onlineMode 1"
                self.parameters_t2s = self.t2scfg+" " + self.gizaoptions + " -onlineMode 1"

		self.giza2bal = self.path + "/scripts/giza2bal.pl"
		self.symal = self.path + "/bin/symal"
		self.mgiza = self.path + "/bin/mgiza"

### CHECK WHETHER commands are available 
##### ............... TODO ...............

		self.err_signal_pattern = re.compile("^Alignment took [0-9]+ seconds")

		self.log_s2t = open(os.devnull, 'w')
		self.log_t2s = open(os.devnull, 'w')
		#self.log_s2t = open("_s2t.gizalog"+str(os.getpid()), 'w')
		#self.log_t2s = open("_t2s.gizalog"+str(os.getpid()), 'w')
                logging.info("MGIZA_CALL:|"+self.mgiza+' '+self.parameters_s2t+"|")
                self.aligner_s2t = subprocess.Popen([self.mgiza]+self.parameters_s2t.split(),
                        stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE,
                        stderr=self.log_s2t,
                        shell=False)
                logging.info("MGIZA_CALL:|"+self.mgiza+' '+self.parameters_t2s+"|")
                self.aligner_t2s = subprocess.Popen([self.mgiza]+self.parameters_t2s.split(),
                        stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE,
                        stderr=self.log_t2s,
                        shell=False)
                logging.info("SYMAL_CALL:|"+self.symal+' '+self.symtype+"|")
                self.symal_proc = subprocess.Popen([self.symal]+self.symtype.split(),  stdin=subprocess.PIPE,  stdout=subprocess.PIPE)

 
        def align(self, source="", target="", correction="", moses_translation_options=""):
		err = []
                logging.info("ALIGNER source:"+source)
                logging.info("ALIGNER correction:"+correction)

# write target and source to a proper string 
                aligner_input_src2trg = "<src>" + correction + "</src><trg>" + source + "</trg>"
                aligner_input_trg2src = "<src>" + source + "</src><trg>" + correction + "</trg>"
		aligner_input_src2trg = aligner_input_src2trg.lower()
		aligner_input_trg2src = aligner_input_trg2src.lower()
		rr = str(random.randint(0,1000000))

#Source-Target          
                logging.info("ALIGNER input s2t:"+aligner_input_src2trg)
                self.aligner_s2t.stdin.write(aligner_input_src2trg+'\n')
                self.aligner_s2t.stdin.flush()

                response_src2trg = self.aligner_s2t.stdout.readline().strip() + '\n'
                response_src2trg = response_src2trg + self.aligner_s2t.stdout.readline().strip() + '\n'
                response_src2trg = response_src2trg + self.aligner_s2t.stdout.readline().strip() + '\n'

                align_src2trg_file = self.tmpdir+"/_s2t"+str(os.getpid())+"_"+rr
                write_to_file(align_src2trg_file, response_src2trg)

                logging.info("ALIGNER output s2t:"+response_src2trg)
#Target-Source          
                logging.info("ALIGNER input t2s:"+aligner_input_trg2src)
                self.aligner_t2s.stdin.write(aligner_input_trg2src+'\n')
                self.aligner_t2s.stdin.flush()

                response_trg2src = self.aligner_t2s.stdout.readline().strip() + '\n'
                response_trg2src = response_trg2src + self.aligner_t2s.stdout.readline().strip() + '\n'
                response_trg2src = response_trg2src + self.aligner_t2s.stdout.readline().strip() + '\n'

                align_trg2src_file = self.tmpdir+"/_t2s"+str(os.getpid())+"_"+rr
                write_to_file(align_trg2src_file, response_trg2src)
                logging.info("ALIGNER output t2s:"+response_trg2src)

#create the giza2bal 
	        giza2bal_options = "-d " + align_trg2src_file + " -i " + align_src2trg_file
                giza2bal_proc = subprocess.Popen([self.giza2bal]+ giza2bal_options.split(),  stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		giza2bal_align1 = giza2bal_proc.stdout.readline().strip()
		giza2bal_align2 = giza2bal_proc.stdout.readline().strip()
		giza2bal_align3 = giza2bal_proc.stdout.readline().strip()
                logging.info("GIZA2BAL s2t:|"+giza2bal_align2+"|")
                logging.info("GIZA2BAL t2s:|"+giza2bal_align3+"|")


#symmetrize the alignments
		self.symal_proc.stdin.write(giza2bal_align1+'\n')
		self.symal_proc.stdin.write(giza2bal_align2+'\n')
		self.symal_proc.stdin.write(giza2bal_align3+'\n')

                alignment = self.symal_proc.stdout.readline().strip()
                logging.info("SYMAL_OUT: "+alignment.strip())

# remove source and target strings	
		alignment = re.sub("^.+{##}[ \t]*",'',alignment)
                logging.info("SYMAL_OUT after string replacement: "+alignment.strip())

                # remove temporary files
                os.remove(align_src2trg_file), os.remove(align_trg2src_file)
                return alignment.strip()


class Aligner_GIZA:
	"""
	Handles constrained search with external scripts.
	"""
        def __init__(self, parser):
                self.parser = parser
                self.aligner = parser.get('tools', 'aligner_path')
                self.s2tcfg = parser.get('annotation', 'src-trg-gizacfg')
                self.t2scfg = parser.get('annotation', 'trg-src-gizacfg')
                try:
                        parser.get('annotation', 'sym-align-type')
                except:
                        parser.set('annotation', 'sym-align-type', 'intersection')
                try:
                        parser.get('annotation', 'models-iterations')
                except:
                        parser.set('annotation', 'models-iterations', 'm4=1')
                try:
			self.mgiza = parser.get('tools', 'mgiza_path')
		except:
			self.mgiza = None
			
                self.symtype = parser.get('annotation', 'sym-align-type')
                self.modeliter = parser.get('annotation', 'models-iterations')
                self.tmpdir = parser.get('env', 'tmp')

        def align(self, source="", target="", correction="", moses_translation_options=""):
		logging.info("SEARCHER source:"+source)
		logging.info("SEARCHER correction:"+correction)
		# extract translation options from Moses output
		# write target and source to temporary files
		rr = str(random.randint(0,1000000))
		crt_file = self.tmpdir+"/_crt"+str(os.getpid())+"_"+rr
		write_to_file(crt_file, correction+'\n')
		src_file = self.tmpdir+"/_src"+str(os.getpid())+"_"+rr
		write_to_file(src_file, source+'\n')

		# call constrained search script
		if self.mgiza:
			logging.info("SEARCHER_CALL: "+str(self.aligner+" --src "+src_file+" --trg "+crt_file+" --gizacfg-src2trg "+self.s2tcfg+" --gizacfg-trg2src "+self.t2scfg+" --sym-type "+self.symtype+" --models-iterations "+self.modeliter+" --mgiza "+self.mgiza))
			aligner = subprocess.Popen([self.aligner,"--src",src_file,"--trg",crt_file,"--gizacfg-src2trg", self.s2tcfg, "--gizacfg-trg2src", self.t2scfg, "--sym-type", self.symtype,"--models-iterations", self.modeliter,"--mgiza",self.mgiza],  stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		else:
			logging.info("SEARCHER_CALL: "+str(self.aligner+" --src "+src_file+" --trg "+crt_file+" --gizacfg-src2trg "+self.s2tcfg+" --gizacfg-trg2src "+self.t2scfg+" --sym-type "+self.symtype+" --models-iterations "+self.modeliter))
			aligner = subprocess.Popen([self.aligner,"--src",src_file,"--trg",crt_file,"--gizacfg-src2trg", self.s2tcfg, "--gizacfg-trg2src", self.t2scfg, "--sym-type", self.symtype,"--models-iterations", self.modeliter],  stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		
		alignment, err = aligner.communicate()
		logging.info("SEARCHER_OUT: "+alignment.strip())
		logging.info("SEARCHER_ERR: "+str(err))

		# remove temporary files
		os.remove(crt_file), os.remove(src_file)
		return alignment.strip()

class Aligner_IBM1:

    def __init__(self, parser):
	self.parser = parser
        self.s2t_lexfile = parser.get('annotation', 'source2target_lexicon')
        self.t2s_lexfile = parser.get('annotation', 'target2source_lexicon')
        try:
            parser.get('annotation', 'epsilon')
        except:
            parser.set('annotation', 'epsilon', '0.000001')
        self.epsilon = float(parser.get('annotation', 'epsilon'))

        logging.info("s2t_lexfile:"+self.s2t_lexfile)
	lexlist = read_file(self.s2t_lexfile)

        self.s2t_model = defaultdict(lambda: dict()) # s t p(s|t)
        for tword, sword, pr in imap(str.split, lexlist):
            self.s2t_model[sword][tword] = float(pr)

        logging.info("t2s_lexfile:"+self.t2s_lexfile)
	lexlist = read_file(self.t2s_lexfile)
        self.t2s_model = defaultdict(lambda: dict()) # s t p(s|t)
        for sword, tword, pr in imap(str.split, lexlist):
            self.t2s_model[tword][sword] = float(pr)

    def align(self, source="", target="", correction="", moses_translation_options=""):
	source_list = source.split()
	correction_list = correction.split()
        I = len(source_list)
        J = len(correction_list)
        Q = self.update(source_list, correction_list, I, J)
###        self.__printQ(Q,True)
        a = self.best_alignment(Q, I, J)
###        return a
        return " ".join(a)

    def update(self, source, correction, I, J):
        Q = [[None]*(I+1) for s in correction] # None means possible but unknown
                                        # I+1 to allow alignment to NULL word
        for j in range(J):
            w_t = correction[j]
            for i in range(I+1):  # a_j
                if not Q[j][i] == None:
                    continue
                w_s = 'NULL'
                if i < I:
                    w_s = source[i]

                #lex_prob = self.s2t_prob(w_s, w_t)
                #lex_prob = self.t2s_prob(w_t, w_s)
                lex_prob = self.s2t_prob(w_s, w_t) + self.t2s_prob(w_s, w_t)
                Q[j][i] = lex_prob
        return Q

    def best_alignment(self, Q, I, J, verbose=False): # backtrace
        """ just picking the best word for every target index """
        alignment = []

        for j in range(J):
            best_idx = I
            best = None
            for i in range(I+1):
                if best == None or Q[j][i] > best:
                    best = Q[j][i];
                    best_idx = i

            if best_idx == I:
                best_idx = -1 # aligned to NULL word means unaligned
            if verbose:
                sys.stderr.write("%s %s -> %s\n" %(j, best_idx, Q[j][best_idx]))
            a_j = best_idx
	    if a_j >= 0:
	        ###alignment.append(str(j)+"-"+str(a_j))
	        alignment.append(str(a_j)+"-"+str(j))

        return alignment

    def _get_prob(self, probs, key1, key2, min_val=0.0):
        """ get value from a dict-of-dicts structure (probs).
            Ignores missing values and returns at least min_val """
        if not key1 in probs:
            return min_val
	return max(min_val, probs[key1].get(key2, 0.0))

    def t2s_prob(self, t, s):
        """ lexical probability of translating target word t as s """
        return self._get_prob(self.t2s_model, t, s, self.epsilon)

    def s2t_prob(self, s, t):
        """ lexical probability of translating source word s as t """
        return self._get_prob(self.s2t_model, s, t, self.epsilon)

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


def usage():
	"""
	Prints script usage.
	"""
	sys.stderr.write("./aligner.py .....\n")

if __name__ == "__main__":
	if not len(sys.argv) == 2:
		usage()
		sys.exit()
	else:
		# parse config file
		parser = SafeConfigParser()
		parser.read(sys.argv[1])

        aligner_type = parser.get('tools', 'aligner_type')

#### TO IMPLEMENT A CASE STUDY
        if aligner_type == "GIZA" :
                Aligner_object = Aligner_GIZA(parser)
        elif aligner_type == "IBM1" :
                Aligner_object = Aligner_IBM1(parser)
        elif aligner_type == "Constrained_Search" :
                Aligner_object = Aligner_Constrained_Search(parser)
        elif aligner_type == "Dummy" :
                Aligner_object = Aligner_Dummy(parser)

        src="modest weather expected"
        src="Defining common system administration tasks"
        crt="atteso tempo modesto"
        crt="Definire attivita &apos; amministrative di sistema comuni"

        sys.stdout.write("SRC: %s\n" %src)
        sys.stdout.write("TRG: %s\n" %crt)

        if aligner_type == "GIZA" :
                a = Aligner_object.align(source=src,correction=crt)
        elif aligner_type == "IBM1" :
                a = Aligner_object.align(source=src,correction=crt)
        elif aligner_type == "Constrained_Search" :
		moses_to = ""
                logging.info("This alignment tool requires the output of Moses containing the translation options")
                if moses_to == "":
			a = "NO_OUTPUT: Moses translation options not provided"
		else:
			a = Aligner_object.align(source=src,correction=crt,moses_translation_options=moses_to)
        else:
	        sys.stdout.write("ALIGN: the alignment is not computed with this type of Alignment tool: %s" % aligner_type)
        	sys.exit(1)

        sys.stdout.write("ALIGN: %s\n" %a)
        sys.stdout.flush()

