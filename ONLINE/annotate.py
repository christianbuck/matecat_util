#!/usr/bin/python

import sys, getopt, logging

def read_file(fn):
	"""
	Read a list of sentences from a file.
	"""
	return [line.strip() for line in open(fn)]

class Annotator_dummy:
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

        def annotate(self, source):
                return source



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
                        parser.get('annotation', 'cbtm_best')
                except:
                        parser.set('annotation', 'cbtm_best', 'False')
                self.cbtm_best = parser.get('annotation', 'cbtm_best')
                logging.info("cbtm_best: "+self.cbtm_best)

		self.n=int(parser.get('annotation', 'cblm_n_gram_level'))
                logging.info("n: "+str(self.n))

                self.filter=parser.get('annotation', 'cblm_filter')
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
                for source, target in new:
                        self.phrases["new"].setdefault(source, []).append(target)
                for source, target in bias:
                        self.phrases["bias"].setdefault(source, []).append(target)
                for source, target in full:
                        self.phrases["full"].setdefault(source, []).append(target)

                for source, target in new:
                        if not target in self.cblm_phrases:
                                self.cblm_phrases.append(target)
                for source, target in bias:
                        if not target in self.cblm_phrases:
                                self.cblm_phrases.append(target)
                for source, target in full:
                        if not target in self.cblm_phrases:
                                self.cblm_phrases.append(target)

        def get_cblm_annotation(self, sentence):
                """
                Return the cache-based language model annotation format for the
                given sentence.
                """
		sentence = sentence.strip()
		n = self.n
                if int(self.cblm_constrained_on_cbtm) == 1:
                        add_to_cache = self.cblm_phrases
                else:
                        n_grams = []
                        tokens = sentence.split()
                        while n:
                                for i in range(len(tokens)-n+1):
                                        entry = " ".join(tokens[i:i+n])
                                        if not entry in n_grams:
                                                n_grams.append(entry)
                                n -= 1

                        if int(self.filter) == 1:
                                #filter out n-grams that only contain stopwords, numbers and tokens
                                #consisting of more than one character
                                add_to_cache = []
                                for ng in n_grams:
                                        for t in ng.split():
                                                ##if len(t) > 1 and not ng.lower() in self.stopwords_target and not ng.isdigit():
                                                if len(t) > 1 and not t.lower() in self.stopwords_target and not t.isdigit():
                                                        if not ng in add_to_cache:
                                                                add_to_cache.append(ng)
                                                        break
                        
                        else:
                                add_to_cache = n_grams

		#always add the full sentence
                add_to_cache.append(sentence)
                
                if not add_to_cache:
                        return ''
                else:
                        return '<dlt cblm="'+'||'.join(add_to_cache)+'"/>'

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
                                #(garbage collectors)
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
                
                if not translations:                        return options, 0.

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
                        parser.get('annotation', 'cbtm_best')
                except:
                        parser.set('annotation', 'cbtm_best', 'False')
                self.cbtm_best = parser.get('annotation', 'cbtm_best')
                logging.info("cbtm_best: "+self.cbtm_best)

                self.n=int(parser.get('annotation', 'cblm_n_gram_level'))
                logging.info("n: "+str(self.n))

                self.filter=parser.get('annotation', 'cblm_filter')
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

                for source, target in new:
                        self.phrases["new"].setdefault(source, []).append(target)
                for source, target in bias:
                        self.phrases["bias"].setdefault(source, []).append(target)
                for source, target in full:
                        self.phrases["full"].setdefault(source, []).append(target)

		for source, target in new:
			if not target in self.cblm_phrases:
                        	self.cblm_phrases.append(target)
                for source, target in bias:
			if not target in self.cblm_phrases:
                        	self.cblm_phrases.append(target)
                for source, target in full:
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
		if int(self.cblm_constrained_on_cbtm) == 1:
			add_to_cache = self.cblm_phrases
		else:
			n_grams = []
			tokens = sentence.split()
			while n:
				for i in range(len(tokens)-n+1):
					entry = " ".join(tokens[i:i+n])
                                	if not entry in n_grams:
                	                	n_grams.append(entry)
				n -= 1

			if int(self.filter) == 1:
				#filter out n-grams that only contain stopwords, numbers and tokens
				#consisting of more than one character
				add_to_cache = []
        			for ng in n_grams:
                			for t in ng.split():
                        			if len(t) > 1 and not ng.lower() in self.stopwords_target and not ng.isdigit():
                                			if not ng in add_to_cache:
                                				add_to_cache.append(ng)
                        	        		break
			
			else:
				add_to_cache = n_grams
		
		if not add_to_cache:
			return ''
		else:
			return '<dlt cblm="'+'||'.join(add_to_cache)+'"/>'

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
				insert=0
				for s in source.split():
                                        if len(s) > 1 and not s.lower() in self.stopwords_source and not s.isdigit():
						insert=1
						break
				if insert == 0:
					continue

				target_phrases = type_phrases[source]
				for target in target_phrases:
					insert=0
					for t in target.split():
                                        	if len(t) > 1 and not t.lower() in self.stopwords_target and not t.isdigit():
							insert=1
                                                        break
 	                                if insert == 0:
        	                                continue
 
					phrasepair = source + "|||" + target
					if not phrasepair in cbtm_phrases:
						cbtm_phrases.append(phrasepair)

                if not cbtm_phrases:
                        return ''
                else:
	                return '<dlt cbtm="'+'||||'.join(cbtm_phrases)+'"/>'


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
		
	global _stopwords_en
	_stopwords_en = read_file("/hltsrv0/waeschle/experiments/scripts/stopwords.en")
	global _stopwords_it
	_stopwords_it = read_file("/hltsrv0/waeschle/experiments/scripts/stopwords.it")
	
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
