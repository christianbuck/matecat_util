
import sys, logging, os
import codecs, subprocess, select, re, logging
from decoder import Decoder_Moses, Decoder_Deterministic 
from aligner import Aligner_GIZA, Aligner_Constrained_Search, Aligner_IBM1, Aligner_Dummy
from phrase_extractor import Extractor_Moses, Extractor_Constrained_Search, Extractor_Dummy
from annotate import Annotator_onlinexml, Annotator_onlinecache

from ConfigParser import SafeConfigParser

logging.basicConfig(level=logging.INFO)

def usage():
	"""
	Prints script usage.
	"""
	sys.stderr.write("./wrapper.py <config.cfg>\n")

if __name__ == "__main__":
	if not len(sys.argv) == 2:
		usage()
		sys.exit()
	else:
		# parse config file
		parser = SafeConfigParser()
		parser.read(sys.argv[1])

	decoder_type = parser.get('tools', 'decoder_type')
	aligner_type = parser.get('tools', 'aligner_type')
	extractor_type = parser.get('tools', 'extractor_type')
	annotator_type = parser.get('tools', 'annotator_type')

	input = open(parser.get('data', 'source'), 'r')
	edit = open(parser.get('data', 'reference'), 'r')


	if decoder_type == "Moses" :
        	Decoder_object = Decoder_Moses(parser)
	elif decoder_type == "Deterministic" :
	        Decoder_object = Decoder_Deterministic(parser)
	else:
		logging.info("This decoder is UNKNOWN")
		sys.exit(1)
	
        if aligner_type == "GIZA" :
        	Aligner_object = Aligner_GIZA(parser)
        elif aligner_type == "Constrained_Search" :
        	Aligner_object = Aligner_Constrained_Search(parser)
		if not decoder_type == "Moses":
                	logging.info("This alignment tool requires Moses as decoder")
                	sys.exit(1)
        elif aligner_type == "Dummy" :
        	Aligner_object = Aligner_Dummy(parser)
		
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
        else:
                logging.info("This annotation tool  is UNKNOWN:")
                sys.exit(1)
	
	# main loop
	# initialize: first sentence has no history
	source = input.readline().strip()
	annotated_source = source
	s_id = 1
	while source:
		logging.info(str(s_id))
		# talk to decoder
		logging.info("DECODER_IN: "+annotated_source)
		decoder_out, decoder_err = Decoder_object.communicate(annotated_source)
		logging.info("DECODER_OUT: "+decoder_out)
		# write translation to stdout
		sys.stdout.write(decoder_out+'\n')
		sys.stdout.flush()
		# now the reference is available
		correction = edit.readline().strip()
		logging.info("SOURCE: "+source)
		logging.info("USER_EDIT: "+correction)

		# get alignment information for the (source,correction)
		aligner_output = Aligner_object.align(source=source,correction=correction,moses_translation_options=decoder_err)
		logging.info("ALIGNER_OUTPUT: "+str(aligner_output))

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

