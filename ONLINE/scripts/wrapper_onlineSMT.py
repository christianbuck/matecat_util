#!/usr/bin/env python

import sys, logging, os
import codecs, subprocess, select, re, logging
import time
import random

from decoder import Decoder_Moses, Decoder_Moses_nbest, Decoder_Deterministic 
from aligner import Aligner_GIZA, Aligner_onlineGIZA, Aligner_Constrained_Search, Aligner_IBM1, Aligner_Dummy
#from aligner import Aligner_GIZA, Aligner_onlineGIZA, Aligner_Constrained_Search, Aligner_IBM1, Aligner_Dummy, Aligner_Pivot
from phrase_extractor import Extractor_Moses, Extractor_Constrained_Search, Extractor_Dummy
from annotate import Annotator_onlinexml, Annotator_onlinecache, Annotator_Dummy

from ConfigParser import SafeConfigParser

logging.basicConfig(level=logging.INFO)

def usage():
	"""
	Prints script usage.
	"""
	sys.stderr.write("./wrapper.py <config.cfg> [-show-weights]\n")

if __name__ == "__main__":
	if not len(sys.argv) >= 2:
		usage()
		sys.exit(1)
	else:
		# parse config file
		parser = SafeConfigParser()
		parser.read(sys.argv[1])

        showweightsflag = ""
        if len(sys.argv) == 3 and sys.argv[2] == "-show-weights":
		sys.stderr.write("sys.argv[2]: |%s|\n" % repr(sys.argv[2]))
                showweightsflag = "-show-weights"
        parser.set('decoder','showweightsflag',showweightsflag)

	rrcode = str(random.randint(0,1000000))

	decoder_type = parser.get('tools', 'decoder_type')
	aligner_type = parser.get('tools', 'aligner_type')
	extractor_type = parser.get('tools', 'extractor_type')
	annotator_type = parser.get('tools', 'annotator_type')

	walign_file = ""
	walignflag = ""

	input = open(parser.get('data', 'source'), 'r')
	edit = open(parser.get('data', 'reference'), 'r')

	decoder_options = ''
	try:
        	decoder_options = parser.get('decoder', 'options')
        except:
        	pass

        parser.set('decoder', 'options', decoder_options) 

        if aligner_type == "Constrained_Search" :
		decoder_options = decoder_options + " -print-translation-option true"

        if decoder_type == "Moses":
                Decoder_object = Decoder_Moses(parser)
                
	elif decoder_type == "Moses_WA":
		logging.info("DECODER_TYPE: "+decoder_type)
		walign_file = parser.get('env', 'tmp') + "/walign_" + rrcode
		walignflag = "active"
		logging.info("DECODER_OPTIONS: "+decoder_options)
		decoder_options = decoder_options + " -alignment-output-file " + walign_file
		parser.set('decoder', 'options', decoder_options)

		logging.info("DECODER_OPTIONS: "+decoder_options)
	
        	Decoder_object = Decoder_Moses(parser)

	elif decoder_type == "Moses_nbest" :
		decoder_nbestfile = '/dev/stdout'
		decoder_nbestsize = '100'
		decoder_nbestdistinct = ''

		try:
			decoder_nbestfile = parser.get('decoder', 'nbestfile')
			if decoder_nbestfile == "-": decoder_nbestfile = '/dev/stdout'
			decoder_options = decoder_options + " " + "-n-best-list -"
                except:
			pass

                try:
			decoder_nbestsize = parser.get('decoder', 'nbestsize')
			decoder_options = decoder_options + " " + decoder_nbestsize
                except:
			pass

                try:
			decoder_nbestdistinct = parser.get('decoder', 'nbestdistinct')
			decoder_options = decoder_options + " " + decoder_nbestdistinct
                except:
			pass

                parser.set('decoder', 'options', decoder_options) 
		decoder_nbestout = open(decoder_nbestfile, 'w')

        	Decoder_object = Decoder_Moses_nbest(parser)

	elif decoder_type == "Deterministic" :
	        Decoder_object = Decoder_Deterministic(parser)
	else:
		logging.info("This decoder is UNKNOWN")
		sys.exit(1)

	if not showweightsflag == "":
		if decoder_type == "Deterministic" :
                	sys.exit(0)

		decoder_out, decoder_err = Decoder_object.show_weights()
		
		# write weights to stdout
		sys.stdout.write(''.join(decoder_out))
		sys.stdout.flush()

		sys.exit(0)

        if aligner_type == "GIZA" :
        	Aligner_object = Aligner_GIZA(parser)
        elif aligner_type == "onlineGIZA" :
                Aligner_object = Aligner_onlineGIZA(parser)
        elif aligner_type == "IBM1" :
                Aligner_object = Aligner_IBM1(parser)
        elif aligner_type == "Constrained_Search" :
        	Aligner_object = Aligner_Constrained_Search(parser)
		if not decoder_type == "Moses" and not decoder_type == "Moses_nbest":
                	logging.info("This alignment tool requires Moses as decoder")
                	sys.exit(1)
        elif aligner_type == "Dummy" :
        	Aligner_object = Aligner_Dummy(parser)
#        elif aligner_type == "Pivot" :
#        	Aligner_object = Aligner_Pivot(parser)
		
        else:
                logging.info("This alignment tool  is UNKNOWN")
                sys.exit(1)

        if extractor_type == "Moses" :
                Extractor_object = Extractor_Moses(parser)
        elif extractor_type == "Constrained_Search" :
                Extractor_object = Extractor_Constrained_Search(parser)
        elif extractor_type == "Dummy" :
                Extractor_object = Extractor_Dummy(parser)
        else:
                logging.info("This extractor tool  is UNKNOWN")
                sys.exit(1)

        if annotator_type == "onlinexml" :
        	Annotator_object = Annotator_onlinexml(parser)
        elif annotator_type == "onlinecache" :
        	Annotator_object = Annotator_onlinecache(parser)
        elif annotator_type == "Dummy" :
        	Annotator_object = Annotator_Dummy(parser)
        else:
                logging.info("This annotation tool  is UNKNOWN:")
                sys.exit(1)

	if not walignflag == "":
		while not os.path.exists(walign_file):		
			time.sleep (1.0 / 10);	
	
		walign = open(walign_file, 'r')
                logging.info("walign_file " + walign_file + " is open ")

	# main loop
	# initialize: first sentence has no history
	source = input.readline().strip()
	annotated_source = source
	s_id = 1

	while source:
		logging.info(str(s_id))
		# talk to decoder
		logging.info("DECODER_IN: "+annotated_source)
                logging.info("DECODER type:|%s|" % decoder_type)
		if decoder_type == "Moses" or decoder_type == "Moses_WA" :
	                decoder_out, decoder_err = Decoder_object.communicate(annotated_source)
        	        logging.info("DECODER_OUT: "+decoder_out)

                	# write translation to stdout
             		sys.stdout.write(decoder_out+'\n')
             		sys.stdout.flush()

        	elif decoder_type == "Moses_nbest" :
                	decoder_nbest, decoder_err = Decoder_object.communicate(annotated_source)

        	        logging.info("DECODER_NBESTFILE: |"+decoder_nbestfile+"|")
			if decoder_nbestfile == "/dev/stdout":
	                # write nbest translations to stdout
	                	sys.stdout.write('\n'.join(decoder_nbest)+'\n')
	                	sys.stdout.flush()
			else:
	                # write nbest translations to file and first best to stdout
	                	decoder_nbestout.write('\n'.join(decoder_nbest)+'\n')
	                	decoder_nbestout.flush()
				firstbest = decoder_nbest[0]
				firstbest = re.sub(r"^[^\|]+\|\|\|\s*","",firstbest)
				firstbest = re.sub(r"\s*\|\|\|.+$","",firstbest)
        	        	logging.info("DECODER_1BEST: "+firstbest)
	                	sys.stdout.write(firstbest+'\n')
	                	sys.stdout.flush()

        	elif decoder_type == "Deterministic" :
                        decoder_out, decoder_err = Decoder_object.communicate(source)
                        logging.info("DECODER_OUT: "+decoder_out)

                        # write translation to stdout
                        sys.stdout.write(decoder_out+'\n')
                        sys.stdout.flush()
	
		# now the reference is available
		correction = edit.readline().strip()
		logging.info("SOURCE: "+source)
		logging.info("USER_EDIT: "+correction)

                # now the source-to-target word-to-2word alignment is available
		wa_s2t = ""
                if not walignflag == "":
			wa_s2t = walign.readline().strip()
                logging.info("WA_S2T: "+wa_s2t)

                if aligner_type == "Pivot" :
			# get alignment information for the (source,correction)
			aligner_output = Aligner_object.align(source=source,target=decoder_out,wa_s2t=wa_s2t,correction=correction,moses_translation_options=decoder_err)
			logging.info("ALIGNER_OUTPUT: "+repr(aligner_output))
		else:
			# get alignment information for the (source,correction)
			aligner_output = Aligner_object.align(source=source,correction=correction,moses_translation_options=decoder_err)
			logging.info("ALIGNER_OUTPUT: "+repr(aligner_output))

		# get phrase pairs form the alignment information
		bias, new, full = Extractor_object.extract_phrases(source,correction,aligner_output)
		logging.info("BIAS: "+str(bias))
		logging.info("NEW: "+str(new))
		logging.info("FULL: "+str(full))
		
                Annotator_object.cbtm_update(new=new, bias=bias, full=full)
                Annotator_object.cblm_update(correction)

                # read and annotate the next sentence
                source = input.readline().strip()
                annotated_source = Annotator_object.annotate(source)

		s_id += 1

