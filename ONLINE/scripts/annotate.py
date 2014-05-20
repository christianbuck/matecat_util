#!/usr/bin/python

## [annotation]
## cblm_constrained_on_cbtm: 1 if cblm suggestions come from the target side of the cbtm suggestions, and not from n-grams
## 			     0 if cblm suggestions come n-grams, and not from the target side of the cbtm suggestions
##			     (default is 0)
## cblm_improved_by_cbtm: 1 if cblm suggestions also come from the target side of the cbtm suggestions (the full target sentence is also added)
##                        0 otherwise
##			     (default is 0)
## cblm_improved_by_full_sentence: 1 if cblm suggestion also include the full target sentence
##                                 0 otherwise (it is still possible that the full target sentence is included, if it is already included in the cbtm suggestions)
##			     (default is 0)

## note that duplicate suggestions are inserted only once

## Parameters valid for annotator_type=onlinexml only
## cbtm_best:	1	suggest only the phrase pair the the highest probability
##		0	otherwise

import sys, getopt, logging

def read_file(fn):
	"""
	Read a list of sentences from a file.
	"""
	return [line.strip() for line in open(fn)]

class Annotator_Dummy:
        def __init__(self, parser):
		self.parser = parser	
                self.tmpdir = parser.get('env', 'tmp')

        def annotate(self, source):
                return source

        def cblm_update(self, correction):
                # construct lm cache annotation
                self.cblm_cache = ""

        def cbtm_update(self, new=[], bias=[], full=[]):
                # construct lm cache annotation
                self.cbtm_cache = ""

class Annotator_onlinexml:
	def __init__(self, parser):
                self.weights = {"new": float(parser.get('annotation', 'w_new')),
                                "bias": float(parser.get('annotation', 'w_bias')),
                                "full": float(parser.get('annotation', 'w_full'))}
                logging.info("self.weights: "+str(self.weights))

                self.levels = {"new": int(float(parser.get('annotation', 'l_new'))),
                               "bias": int(float(parser.get('annotation', 'l_bias'))),
                               "full": int(float(parser.get('annotation', 'l_full')))}
                logging.info("self.levels: "+str(self.levels))

	        self.cblm_annotation = int(parser.get('annotation', 'cblm'))
	        if self.cblm_annotation:
	                logging.info("CBLM annotation is active")
	        else:
        	        logging.info("CBLM annotation is not active")

	        self.cbtm_annotation = int(parser.get('annotation', 'cbtm'))
                if self.cbtm_annotation:
                        logging.info("CBTM annotation is active")
                else:   
                        logging.info("CBTM annotation is not active")

                self.factor = float(parser.get('annotation', 'factor'))

        	try:
                	parser.get('annotation', 'cblm_constrained_on_cbtm')
        	except:
                	parser.set('annotation', 'cblm_constrained_on_cbtm', '0')
	        logging.info("cblm_constrained_on_cbtm: "+parser.get('annotation', 'cblm_constrained_on_cbtm'))
                self.cblm_constrained_on_cbtm = int(parser.get('annotation', 'cblm_constrained_on_cbtm'))

                try:
                        parser.get('annotation', 'cblm_improved_by_cbtm')
                except:
                        parser.set('annotation', 'cblm_improved_by_cbtm', '0')
                logging.info("cblm_improved_by_cbtm: "+parser.get('annotation', 'cblm_improved_by_cbtm'))
                self.cblm_improved_by_cbtm = int(parser.get('annotation', 'cblm_improved_by_cbtm'))

                try:
                        parser.get('annotation', 'cblm_improved_by_full_sentence')
                except:
                        parser.set('annotation', 'cblm_improved_by_full_sentence', '0')
                logging.info("cblm_improved_by_full_sentence: "+parser.get('annotation', 'cblm_improved_by_full_sentence'))
                self.cblm_improved_by_full_sentence = int(parser.get('annotation', 'cblm_improved_by_full_sentence'))



                try:
                        parser.get('annotation', 'cbtm_best')
                except:
                        parser.set('annotation', 'cbtm_best', 'False')
                self.cbtm_best = parser.get('annotation', 'cbtm_best')
                logging.info("cbtm_best: "+self.cbtm_best)

		self.n=int(parser.get('annotation', 'cblm_n_gram_level'))
                logging.info("n: "+str(self.n))

                self.cblm_filter=parser.get('annotation', 'cblm_filter')
                self.cbtm_filter=parser.get('annotation', 'cbtm_filter')
                self.stopwords_source = [l.strip() for l in open(parser.get('data', 'stopwords_source'))]
                self.stopwords_target = [l.strip() for l in open(parser.get('data', 'stopwords_target'))]

                self.phrases = {"new": {}, "bias": {}, "full": {}}
                self.cblm_phrases = []

	def annotate(self, source):
	        if self.cbtm_annotation:
                        annotated_source = self.annotate_sentence(source)
                else:
                        annotated_source = source
		annotated_source = annotated_source + self.cblm_cache
                return annotated_source

        def clear(self):
                """
                clear phrase translation dictionaries.
                """
                self.phrases = {"new": {}, "bias": {}, "full": {}}
                self.cblm_phrases = []

        def cblm_update(self, correction):
                # construct lm cache annotation
                self.cblm_cache = ""
                if self.cblm_annotation:
                        self.cblm_cache = self.get_cblm_annotation(correction)
                        logging.info("CBLM_CACHE "+self.cblm_cache)

        def cbtm_update(self, new=[], bias=[], full=[]):
                """
                Update phrase translation dictionaries.
                """
                for source, target, wa in new:
                        self.phrases["new"].setdefault(source, []).append(target, wa)
                for source, target, wa in bias:
                        self.phrases["bias"].setdefault(source, []).append(target, wa)
                for source, target, wa in full:
                        self.phrases["full"].setdefault(source, []).append(target, wa)

                for source, target, wa in new:
                        if not target in self.cblm_phrases:
                                self.cblm_phrases.append(target)
                for source, target, wa in bias:
                        if not target in self.cblm_phrases:
                                self.cblm_phrases.append(target)
                for source, target, wa in full:
                        if not target in self.cblm_phrases:
                                self.cblm_phrases.append(target)

        def get_cblm_annotation(self, sentence):
                """
                Return the cache-based language model annotation format for the
                given sentence.
                """
		sentence = sentence.strip()
		n = self.n
                add_to_cache = []
                n_grams = []

## (optionally) add all target phrases suggested to the cbtm
                if int(self.cblm_improved_by_cbtm) == 1:
                        n_grams = self.cblm_phrases

## (optionally) add the full sentence 
                if int(self.cblm_improved_by_full_sentence) == 1:
                        if not sentence in n_grams:
                                n_grams.append(sentence)

                if int(self.cblm_constrained_on_cbtm) == 1:
## add only target phrases suggested to the cbtm
                        for ng in self.cblm_phrases:
                                n_grams.append(ng)
                else:
## add all n-grams
                        tokens = sentence.split()
                        while n:
                                for i in range(len(tokens)-n+1):
                                        entry = " ".join(tokens[i:i+n])
                                        if not entry in n_grams:
                                                n_grams.append(entry)
                                n -= 1

                if int(self.cblm_filter) == 1:
                        #filter out n-grams that only contain stopwords, numbers and tokens
                        #consisting of more than one character
                        for ng in n_grams:
                                for t in ng.split():
                                        if len(t) > 1 and not ng.lower() in self.stopwords_target and not ng.isdigit():
                                                if not ng in add_to_cache:
                                                        add_to_cache.append(ng)
                                                break
                else:
                        for ng in n_grams:
                                if not ng in add_to_cache:
                                        add_to_cache.append(ng)

                if not add_to_cache:
                        return ''
                else:
                        return '<dlt type=cbtm cblm="'+'||'.join(add_to_cache)+'"/>'

        def annotate_sentence(self, sentence):
                """
                Return a sentence string annotated with translation 
                suggestions from the cache of all previously translated sentence.
                """
                tokens = sentence.split(' ')

                for phrases in self.phrases.values():
                        if phrases:
                                break
                else:
                        return sentence

                levels = {}
                for pt in self.levels.keys():
                        if self.levels[pt] < 0:
                                levels[pt] = len(tokens)
                        else:
                                levels[pt] = self.levels[pt]
                        if self.weights[pt] == 0:
                                levels[pt] = 0
                        
                n = 0
                if levels:
                        n = max(levels.values())

                #keep track of annotated spans
                annotated = [0 for token in tokens]
        
                #search for phrases on all n-gram levels; higher n is preferred
                while n > 0:
                        for i in range(len(tokens)-n+1):
                                if 1 in annotated[i:i+n]:
                                        #already found an higher n-gram overlapping translation
                                        continue

                                n_gram = tokens[i:i+n]
                                phrase = ' '.join(n_gram)

                                #stopword translations are often based on incorrect alignments
                                #(garbage collectors
                                if int(self.cbtm_filter) == 1:
					## filter out phrase pair, if the source side is composed only by  words (<2), stopwords, or digits 
	                                if not [w for w in n_gram if not (w.isdigit() or w.lower() in self.stopwords_source or len(w) < 2)]:
        	                                continue
                                        
                                freq_dict = {"full": {}, "new": {}, "bias": {}}
                                count = {"full": 0., "new": 0., "bias": 0.}
                                
                                for source in ["full", "new", "bias"]:
                                        if not n > levels[source]:
                                                freq_dict[source], count[source] = self.get_option_freq(self.phrases[source].get(phrase), self.weights[source])
                                
                                for phrases in freq_dict.values():
                                        if phrases:
                                                break
                                else:
                                        continue

                                n_options = 0.
                                for c in count.values():
                                        n_options += c

                                if not n_options:
                                        continue

                                all_options = {}

                                for source, options in freq_dict.items():
                                        for option, freq in options.items():
                                                all_options[option] = all_options.get(option, 0)+(freq/n_options)*self.factor

                                if self.cbtm_best:
                                        best_options = []
                                        max_prob = max([prob for option, prob in all_options.items()])
                                        for option, prob in all_options.items():
                                                if prob == max_prob:
                                                        best_options.append((option, prob))
                                else:
                                        best_options = all_options.items()

                                translation_string = "||".join([option for option, prob in best_options])
                                probability_string = "||".join([str(prob) for option, prob in best_options])
                                translation = 'translation="'+translation_string+'" pr="'+probability_string+'"'                        

                                #annotate phrase, if translation (without XML markup characters) was found
                                if translation and not '/' in translation:
                                        tokens[i] = '<phrase ' + translation +'>'+tokens[i]
                                        tokens[i+n-1] = tokens[i+n-1]+'</phrase>'
                                        #remember which part was annotated to prevent overlap
                                        for j in range(i, i+n):
                                                annotated[j] = 1
                        n -= 1
        
                return " ".join(tokens)

        def get_option_freq(self, translations, weight):
                """
                Return weighted translation options and frequencies.
                """
                options = {}
                n_options = 0.
                
                if not translations:
			return options, 0.

                for translation in translations:
                                options[translation] = options.setdefault(translation, 0.)+1.*weight
                                n_options += 1.*weight
                                
                return options, n_options

class Annotator_onlinecache:
        def __init__(self, parser):
                self.cblm_annotation = int(parser.get('annotation', 'cblm'))
                logging.info("self.cblm_annotation: "+str(self.cblm_annotation))
                if self.cblm_annotation:
                        logging.info("CBLM annotation is active")
                else:
                        logging.info("CBLM annotation is not active")

                self.cbtm_annotation = int(parser.get('annotation', 'cbtm'))
                logging.info("self.cbtm_annotation: "+str(self.cbtm_annotation))
                if self.cbtm_annotation:
                        logging.info("CBTM annotation is active")
                else:   
                        logging.info("CBTM annotation is not active")

                try:
                        parser.get('annotation', 'cblm_constrained_on_cbtm')
                except:
                        parser.set('annotation', 'cblm_constrained_on_cbtm', '0')
                logging.info("cblm_constrained_on_cbtm: "+parser.get('annotation', 'cblm_constrained_on_cbtm'))
                self.cblm_constrained_on_cbtm = int(parser.get('annotation', 'cblm_constrained_on_cbtm'))

                try:
                        parser.get('annotation', 'cblm_improved_by_cbtm')
                except:
                        parser.set('annotation', 'cblm_improved_by_cbtm', '0')
                logging.info("cblm_improved_by_cbtm: "+parser.get('annotation', 'cblm_improved_by_cbtm'))
                self.cblm_improved_by_cbtm = int(parser.get('annotation', 'cblm_improved_by_cbtm'))
                
                try:
                        parser.get('annotation', 'cblm_improved_by_full_sentence')
                except:
                        parser.set('annotation', 'cblm_improved_by_full_sentence', '0')
                logging.info("cblm_improved_by_full_sentence: "+parser.get('annotation', 'cblm_improved_by_full_sentence'))
                self.cblm_improved_by_full_sentence = int(parser.get('annotation', 'cblm_improved_by_full_sentence'))

                self.n=int(parser.get('annotation', 'cblm_n_gram_level'))
                logging.info("n: "+str(self.n))

                try:
                        parser.get('annotation', 'cbtm_id')
                except:
                        parser.set('annotation', 'cbtm_id', '')
                logging.info("cbtm_id: "+parser.get('annotation', 'cbtm_id'))

                try:
                        parser.get('annotation', 'cblm_id')
                except:
                        parser.set('annotation', 'cblm_id', '')
                logging.info("cblm_id: "+parser.get('annotation', 'cblm_id'))


		self.cbtm_id = parser.get('annotation', 'cbtm_id')
		self.cblm_id = parser.get('annotation', 'cblm_id')
                self.cblm_filter=parser.get('annotation', 'cbtm_filter')
                self.cbtm_filter=parser.get('annotation', 'cblm_filter')
                self.stopwords_source = [l.strip() for l in open(parser.get('data', 'stopwords_source'))]
                self.stopwords_target = [l.strip() for l in open(parser.get('data', 'stopwords_target'))]

                self.phrases = {"new": {}, "bias": {}, "full": {}}
                self.cblm_phrases = []

        def annotate(self, source):
                annotated_source = source + self.cbtm_cache + self.cblm_cache
                return annotated_source

        def clear(self):
                """
                clear phrase translation dictionaries.
                """
		self.phrases = {"new": {}, "bias": {}, "full": {}}
		self.cblm_phrases = []

        def cblm_update(self, correction):
                # construct lm cache annotation
                self.cblm_cache = ""
                if self.cblm_annotation:
                        self.cblm_cache = self.get_cblm_annotation(correction)
                        logging.info("CBLM_CACHE "+self.cblm_cache)

	def cbtm_update(self, new=[], bias=[], full=[]):
                """
		Update phrase translation dictionaries.
		"""
		self.clear()

                for source, target, wa in new:
                        self.phrases["new"].setdefault(source, []).append([target, wa])
                for source, target, wa in bias:
                        self.phrases["bias"].setdefault(source, []).append([target, wa])
                for source, target, wa in full:
                        self.phrases["full"].setdefault(source, []).append([target, wa])

		for source, target, wa in new:
			if not target in self.cblm_phrases:
                        	self.cblm_phrases.append(target)
                for source, target, wa in bias:
			if not target in self.cblm_phrases:
                        	self.cblm_phrases.append(target)
                for source, target, wa in full:
			if not target in self.cblm_phrases:
                        	self.cblm_phrases.append(target)

                # construct tm cache annotation
                self.cbtm_cache = ""
                if self.cbtm_annotation:
                        self.cbtm_cache = self.get_cbtm_annotation()
                        logging.info("CBTM_CACHE "+self.cbtm_cache)


	def get_cblm_annotation(self, sentence):
		"""
		Return the cache-based language model annotation format for the
		given sentence.
		"""
                sentence = sentence.strip()
                n = self.n
                add_to_cache = []
		n_grams = []

## (optionally) add all target phrases suggested to the cbtm
                if int(self.cblm_improved_by_cbtm) == 1:
                        n_grams = self.cblm_phrases

## (optionally) add the full sentence 
                if int(self.cblm_improved_by_full_sentence) == 1:
                        if not sentence in n_grams:
                                n_grams.append(sentence)

		if int(self.cblm_constrained_on_cbtm) == 1:
## add only target phrases suggested to the cbtm
        		for ng in self.cblm_phrases:
				n_grams.append(ng)
		else:
## add all n-grams
			tokens = sentence.split()
			while n:
				for i in range(len(tokens)-n+1):
					entry = " ".join(tokens[i:i+n])
                                	if not entry in n_grams:
                	                	n_grams.append(entry)
				n -= 1

		if int(self.cblm_filter) == 1:
			#filter out n-grams that only contain stopwords, numbers and tokens
			#consisting of more than one character
        		for ng in n_grams:
                		for t in ng.split():
                       			if len(t) > 1 and not ng.lower() in self.stopwords_target and not ng.isdigit():
                               			if not ng in add_to_cache:
                               				add_to_cache.append(ng)
                       	        		break
		else:
        		for ng in n_grams:
                               	if not ng in add_to_cache:
					add_to_cache.append(ng)

                logging.info("inside CBLM_CACHE "+repr(add_to_cache))
		
#		if not add_to_cache:
#			return ''
#		else:
#			return '<dlt cblm="'+'||'.join(add_to_cache)+'"/>'

		cblmstr = ''
                if add_to_cache:
                        cblmstr = '<dlt'
                        cblmstr += ' type="cblm"'
                        if self.cblm_id != '':
                                cblmstr += ' id="' + self.cblm_id + '"'
                        cblmstr += ' cblm="'+'||'.join(add_to_cache)
                        cblmstr += '"/>'
		return cblmstr


        def get_cbtm_annotation(self):
                """
                Return a sentence string annotated with translation 
                suggestions from the cache of all previously translated sentence.
                """
                cbtm_phrases = []

                for phrases in self.phrases.values():
                        if phrases:
                                break
                else:
                       	return ''

		for type in ["full", "new", "bias"]:
			type_phrases = self.phrases[type]
			for source in type_phrases:

				if int(self.cbtm_filter) == 1:
					## filter out phrase pair, if composed only by short words (<2), stopwords, or digits, in both source and target side
					insert=0
					for s in source.split():
                                        	if len(s) > 1 and not s.lower() in self.stopwords_source and not s.isdigit():
							insert=1
							break
					if insert == 0:
						continue


				targetWA_phrases = type_phrases[source]
				for target, wa in targetWA_phrases:
	                                if int(self.cbtm_filter) == 1:
						insert=0
						for t in target.split():
                	                        	if len(t) > 1 and not t.lower() in self.stopwords_target and not t.isdigit():
								insert=1
                                	                        break
						if insert == 0:
        	                               		continue
 
					phrasepair = source + "|||" + target + "|||" + wa
					if not phrasepair in cbtm_phrases:
						cbtm_phrases.append(phrasepair)

#                if not cbtm_phrases:
#                        return ''
#                else:
#	                return '<dlt cbtm="'+'||||'.join(cbtm_phrases)+'"/>'

                cbtmstr = ''
                if cbtm_phrases:
                        cbtmstr = '<dlt'
                        cbtmstr += ' type="cbtm"'
                        if self.cbtm_id != '':
                                cbtmstr += ' id="' + self.cbtm_id + '"'
                        cbtmstr += ' cbtm="'+'||||'.join(cbtm_phrases)
                        cbtmstr += '"/>'
                return cbtmstr

def usage():
        """
        Prints script usage.
        """
        sys.stderr.write("./annotate.py xxxxxxx\n")

if __name__ == "__main__":
	try:
		opts, args = getopt.getopt(sys.argv[1:], "n:b:t:h", [	"help",
			"new=",  "bias=", "full-translation=",
			"n-weight=", "b-weight=", "t-weight=",
			"cblm=", "weight-factor=",
			"cbtm_best", "lmfilter", "history=",
			])

	except getopt.GetoptError:
		usage()
		sys.exit()

	new = []
	bias = []
	full = []
	cblm = []
	factor = 1.0
	lmfilter = False
	cbtm_best = False
	history = 1

	for opt, arg in opts:
		if opt in ("-h", "--help"):
			help()
			sys.exit()
		elif opt in ("-n", "--new"):
			new = read_file(arg)
		elif opt in ("-b", "--bias"):
			bias = read_file(arg)
		elif opt in ("-t", "--full-translation"):
			full = read_file(arg)
		elif opt in ("--cblm"):
			cblm = read_file(arg)
		elif opt in ("--lmfilter"):
			lmfilter = True
		elif opt in ("--cbtm_best"):
			cbtm_best = True
		elif opt in ("--history"):
			try:
				history = int(arg)
                        except TypeError:
                                sys.stderr.write("Invalid history parameter.\n")
                                usage()
                                exit()
			if history < 1:
				sys.stderr.write("Invalid history parameter.\n")
				exit()
		else:	
			sys.stderr.write("Invalid option.\n")
			usage()
			sys.exit()
			
	if not len(args) == 1:
		sys.stderr.write("No file to annotate.\n")
		usage()
		sys.exit()

	if not new and not bias and not full and not cblm:
		sys.stderr.write("No annotation file.\n")
		usage()		
		sys.exit()

	fn = args[0]
	text = read_file(fn)
	
	if not len_test(text, new, bias, full, cblm):
		sys.stderr.write("Different file lengths.\n")
		usage()
		sys.exit()
		
	suffix = ".ann"
	if cblm:
		if lmfilter:
			suffix = ".cblm.filtered"+suffix
		else:
			suffix = ".cblm"+suffix
	if not factor:
		suffix = ".uniform"+suffix
	elif factor != 1.0:
		suffix = ".wf_"+str(factor)+suffix
	if new:
		suffix = ".new_w_"+str(weights["new"])+suffix
	if bias:
		suffix = ".bias_w_"+str(weights["bias"])+suffix
	if full:
 		suffix = ".full_w_"+str(weights["full"])+suffix
 	if cbtm_best:
 		suffix = ".best"+suffix
	if history != 1:
		suffix = ".hist_"+str(history)+suffix

	
	out = open(fn+suffix, 'w')

	print "Writing to", fn+suffix, "..."	

	out.write(Annotator(new, bias, full, weights, factor, cbtm_best).annotate(text, cblm, lmfilter, history))
	out.close()
