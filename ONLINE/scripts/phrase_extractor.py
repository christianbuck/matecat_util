#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys, getopt, logging, os, re
import subprocess
import random

from ConfigParser import SafeConfigParser

logging.basicConfig(level=logging.INFO)

def usage():
        """
        Prints script usage.
        """
        sys.stderr.write("./phrase_exractor.py xxxxxxx\n")

def read_file(fn):
        """
        Read a list of sentences from a file.
        """
        try:
                return [line.strip() for line in open(fn)]
        except IOError:
                sys.stderr.write("Could not open file "+fn+"\n")
                sys.exit()

def write_to_file(fn, output):
        """
        Write output to file named fn.
        """
        f = open(fn, 'w')
        f.write(output)
        f.close()

class Extractor_Dummy:
        def __init__(self, parser):
                self.parser = parser
                self.tmpdir = parser.get('env', 'tmp')

        def extract_phrases(self, source, target, constrained_search_out):
                """
                Extract new and used (bias) phrase pairs from constrained sear
ch output.
                """
                applied_pairs = []
                new_pairs = []
                full_pairs = [(source, target)]

                return applied_pairs, new_pairs, full_pairs


class Extractor_Constrained_Search:
        def __init__(self, parser):
                self.parser = parser
                self.tmpdir = parser.get('env', 'tmp')
		self.empty_wa = ""

	def extract_phrases(self, source, target, constrained_search_out):
        	"""
	        Extract new and used (bias) phrase pairs from constrained search output.
	        """
	        target_alignment, source_coverage = self.split_line(constrained_search_out)
        
	        s_tok = [tok.strip() for tok in source.split(' ')]

	        #find uncovered source phrases
	        s_unalgn = []
	        i = 0
	        while i < len(source_coverage):
	                phrase = ''
	                while i < len(source_coverage) and source_coverage[i] == '0':
	                        phrase += s_tok[i]+' '
	                        i += 1
	                i += 1

	                if phrase:
	                        s_unalgn.append(phrase.strip())

	        #parse target sentence and alignment
	        prog = re.compile("(.+?) \[([\d-]+)\]$")
	        t_prs = []
	        for phrase in re.findall(".+? \[[\d-]+\]", target_alignment):
	                phrase = phrase.strip(' ')
	                tmp = prog.match(phrase)
	                t_prs.append([tmp.group(1), tmp.group(2)])
                
	        #construct phrase pairs from alignment
	        t_unalgn = []
	        applied_pairs = []
	        new_pairs = []
		full_pairs = []

	        i = 0
		#create empty word alignment between source and target words
	        while i < len(t_prs):
	                tok, algn = t_prs[i]
	                #unaligned target span
	                if algn == "-1":
	                        phrase = ''
	                        while algn == "-1":
	                                phrase += tok.strip()+' '
	                                if i+1 < len(t_prs):
 	                                       i += 1
 	                                       tok, algn = t_prs[i]
	 	                        else:
 	                                       break
                        	if phrase:
                        	        t_unalgn.append(phrase.strip())
                	#aligned target span (more than one word)
                	elif '-' in algn:
                        	a, b = algn.strip().split('-')
                        	applied_pairs.append((' '.join(s_tok[int(a):int(b)+1]), tok.strip(), self.empty_wa))
                	#aligned target word    
                	else:
                	        applied_pairs.append((s_tok[int(algn)].strip(), tok.strip(), self.empty_wa))

	                i += 1

	        s_unalgn, t_unalgn = self.filter_phrases(s_unalgn), self.filter_phrases(t_unalgn)

		#create many-to many word alignment between source and target words
		wa = self.create_word_alignment(len(s_unalgn_tok), len(t_unalgn_tok))
		
	        #if a one-to-one corrspondence of unaligned source and target span was found,
		#add as new phrase pair
	        if len(s_unalgn) == 1 and len(s_unalgn) == len(t_unalgn):
	                new_pairs.append((s_unalgn.pop(), t_unalgn.pop()), wa)
	        #if no correspondance is found on phrase level, look at token level
	        elif s_unalgn and t_unalgn:
	                s_unalgn_tok = self.split_phrase(s_unalgn)
	                t_unalgn_tok = self.split_phrase(t_unalgn)
	                if len(s_unalgn_tok) == 1 and len(t_unalgn_tok) == 1:
	                        new_pairs.append((s_unalgn_tok.pop(), t_unalgn_tok.pop()), wa)
	                else:
	                        new_pairs += self.align(s_unalgn_tok, t_unalgn_tok, wa)

		full_pairs = [(source, target, wa)]

	        return applied_pairs, new_pairs, full_pairs

	def create_word_alignment(self, s_len, t_len):
		wa = ""
		for i in range(s_len):
			for j in range(t_len):
				wa += str(i) + "-" + str(j) + " "
		return wa

        def split_line(self, line):
                """
                Process constrained search output.
                """
                alignment = line.strip()
                coverage, target_alignment = alignment.split(" : ", 1)
                source_coverage, s1, s2 = coverage.split(' ')

                return target_alignment, source_coverage

	def filter_phrases(self, phrases):
		"""
	        Remove phrases that only consist of words shorter than 3 characters
	        """
	        filtered = []
	        for p in phrases:
	                for t in p.split():
	                        if len(t) > 2:
	                                filtered.append(p)
	                                break
	        return filtered

	def split_phrase(self, phrases):
	        """
	        Split a list of phrase into tokens and remove non-content tokens.
	        """
	        tokens = []
	        for p in phrases:
	                for tok in p.split():
	                        if not len(tok) < 3 and not tok.isdigit():
	                                tokens.append(tok)
	        return tokens

	def align(self, s_tok, t_tok):
	        """
	        Align unaligned words in source and target using a dictionary lookup.
	        """
	        pairs = []
	        for s in s_tok:
	                for t in t_tok:
	                        s.lower()
	                        t.lower()
	                        #TODO: Lookup in word translation tables and previous pairs.    
	        return pairs

	def write_pairs(self, pairs, f):
	        """
	        Write phrase pairs to file.
	        """
	        out = ''
	        for p in pairs:
	                out += ' ||| '.join(p)+"\t"
	        out = out.strip("\t")
	        f.write(out+'\n')
 

class Extractor_Moses:
        def __init__(self, parser):
                self.parser = parser
                self.extractor_script = parser.get('tools', 'extractor_path')
		self.empty_wa = "X-X"
                self.tmpdir = parser.get('env', 'tmp')
                self.PPlen = parser.get('annotation', 'cbtm_phrase_length')
                logging.info("self.extractor_script: "+self.extractor_script)
                logging.info("self.PPlen: "+str(self.PPlen))

        def extract_phrases(self, source, target, giza_symmetrized_alignment):
                """
                Return output and error of the decoder for the given input.
                """

                logging.info("extract_phrases: source:|"+source+"|")
                logging.info("extract_phrases: target:|"+target+"|")
                logging.info("extract_phrases: align:|"+giza_symmetrized_alignment+"|")

                # write target, source, and alignment temporary files
                rr = str(random.randint(0,1000000))
                trg_file = self.tmpdir+"/_trg"+str(os.getpid())+"_"+rr
                write_to_file(trg_file, target+'\n')
                src_file = self.tmpdir+"/_src"+str(os.getpid())+"_"+rr
                write_to_file(src_file, source+'\n')
                align_file = self.tmpdir+"/_align"+str(os.getpid())+"_"+rr
                write_to_file(align_file, giza_symmetrized_alignment+'\n')

                #prepare temporary file for storing the phrase pairs
                PP_file = self.tmpdir+"/_PP"+str(os.getpid())+"_"+rr

                # call extractor search script
                logging.info("EXTRACTOR_CALL: "+self.extractor_script +" "+trg_file+" "+src_file+" "+align_file+" "+PP_file+" "+str(self.PPlen))
		extractor = subprocess.Popen([self.extractor_script, trg_file, src_file, align_file, PP_file, str(self.PPlen)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

                out, err = extractor.communicate()
                logging.info("EXTRACTOR_OUT: "+str(out))
                logging.info("EXTRACTOR_ERR: "+str(err))

		PP_stream = open(PP_file, 'r')

		PP = PP_stream.readline().strip()
        	bias_pairs = []
        	new_pairs = []
        	full_pairs = []

		while PP:
			tokens = PP.split("|||", 3)

			src = tokens[0].strip()
			trg = tokens[1].strip()
			wa = tokens[2].strip()

			bias_pairs.append((src, trg, wa))
		
			PP = PP_stream.readline().strip()
	
###		full_pairs = [(source, target, self.empty_wa)]
		full_pairs = [(source, target, giza_symmetrized_alignment)]

                # remove temporary files
                os.remove(trg_file), os.remove(src_file), os.remove(align_file)
		os.remove(PP_file), os.remove(PP_file+".inv")

                return bias_pairs, new_pairs, full_pairs

if __name__ == "__main__":
	try:
		opts, args = getopt.getopt(sys.argv[1:], "l:h", [ "help", "length" ] )
	except getopt.GetoptError:
		usage()
		sys.exit()

	PPlen = 4

	for opt, arg in opts:
		if opt in ("-h", "--help"):
			help()
			sys.exit()
		elif opt in ("-l", "--length"):
			PPlen = read_file(arg)
		else:	
			sys.stderr.write("Invalid option.\n")
			usage()
			sys.exit()
			
#	if not len(args) == 1:
#		sys.stderr.write("No file to extract from.\n")
#		usage()
#		sys.exit()

#	if not new and not bias and not full and not cblm:
#		sys.stderr.write("No annotation file.\n")
#		usage()		
#		sys.exit()
	
	script = "/path/to/moses/bin//bin/extract"
	tmpdir = "/tmp"

	extractor = Extractor(script, tmpdir, PPlen)
	
	src_txt = "AAA BBB"
	tgt_txt = "CCC DDD"
	align_txt = "0-0 0-1 1-0"

	PP = extractor.extract_phrases(src_txt, tgt_txt, align_txt)
	logging.info("returning PP list: "+str(PP))
