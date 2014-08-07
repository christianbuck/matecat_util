#!/usr/bin/env python
import sys
import threading
import subprocess
import cherrypy
import json
import logging
import time
import re
import xmlrpclib
import math
from threading import Timer
from aligner import mgiza, symal, aligner
from tokentracker import tokentracker
from confidence import wpp

def popen(cmd):
    cmd = cmd.split()
    logger = logging.getLogger('translation_log.popen')
    logger.info("executing: %s" %(" ".join(cmd)))
    return subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE)

def pclose(pipe):
    def kill_pipe():
        pipe.kill()
    t = Timer(5., kill_pipe)
    t.start()
    pipe.terminate()
    t.cancel()

def init_log(filename):
    logger = logging.getLogger('translation_log')
    logger.setLevel(logging.DEBUG)
    fh = logging.FileHandler(filename)
    fh.setLevel(logging.DEBUG)
    logformat = '%(asctime)s %(thread)d - %(filename)s:%(lineno)s: %(message)s'
    formatter = logging.Formatter(logformat)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

def geometric_mean(log_probs):
    try:
        return math.exp(sum(log_probs)) ** (1./len(log_probs))
    except:
        return 0

class Filter(object):
    def __init__(self, remove_newlines=True, collapse_spaces=True):
        self.filters = []
        if remove_newlines:
            self.filters.append(self.__remove_newlines)
        if collapse_spaces:
            self.filters.append(self.__collapse_spaces)

    def filter(self, s):
        for f in self.filters:
            s = f(s)
        return s

    def __remove_newlines(self, s):
        s = s.replace('\r\n',' ')
        s = s.replace('\n',' ')
        return s

    def __collapse_spaces(self, s):
        return re.sub('\s\s+', ' ', s)

def json_error(status, message, traceback, version):
    err = {"status":status, "message":message, "traceback":traceback, "version":version}
    return json.dumps(err, sort_keys=True, indent=4)

class ExternalProcessor(object):
    """ wraps an external script and does utf-8 conversions, is thread-safe """
    # TODO: timeout, restart-every

    def __init__(self, cmd):
        self.cmd = cmd
        if self.cmd != None:
            self.proc = popen(cmd)
            self._lock = threading.Lock()

    def process(self, line):
        if self.cmd == None: return line
        u_string = u"%s\n" %line
        u_string = u_string.encode("utf-8")
        result = u_string  #fallback: return input
        with self._lock:
            self.proc.stdin.write(u_string)
            self.proc.stdin.flush()
            result = self.proc.stdout.readline()
        return result.decode("utf-8").strip()
        # should be rstrip but normalize_punctiation.perl inserts space
        # for lines starting with '('

class ExternalProcessors(object):
    """ single object that does all the pre- and postprocessing """

    def _exec(self, procs):
        def f(line):
            for proc in procs:
                line = proc.process(line)
            return line
        return f

    def __init__(self, tokenizer_cmd, truecaser_cmd, prepro_cmds,
                 annotator_cmds, extractor_cmds, postpro_cmds,
                 detruecaser_cmd, detokenizer_cmd):
        self._tokenizer = map(ExternalProcessor, tokenizer_cmd)
        self.tokenize = self._exec(self._tokenizer)
        self._truecaser = map(ExternalProcessor, truecaser_cmd)
        self.truecase = self._exec(self._truecaser)
        self._preprocessors = map(ExternalProcessor, prepro_cmds)
        self.prepro = self._exec(self._preprocessors)
        self._annotators = map(ExternalProcessor, annotator_cmds)
        self.annotate =  self._exec(self._annotators)
        self._extractors = map(ExternalProcessor, extractor_cmds)
        self.extract = self._exec(self._extractors)
        self._postprocessors = map(ExternalProcessor, postpro_cmds)
        self.postpro = self._exec(self._postprocessors)
        self._detruecaser = map(ExternalProcessor,detruecaser_cmd)
        self.detruecase = self._exec(self._detruecaser)
        self._detokenizer = map(ExternalProcessor,detokenizer_cmd)
        self.detokenize = self._exec(self._detokenizer)

class Root(object):
    required_params = ["q", "key", "target", "source"]

    def __init__(self, moses_url, external_processors, tgt_external_processors,
                 bidir_aligner=None,
                 slang=None, tlang=None, pretty=False, verbose=0, timeout=-1):
        self.filter = Filter(remove_newlines=True, collapse_spaces=True)
        self.moses_url = moses_url
        self.external_processors = external_processors
        self.tgt_external_processors = tgt_external_processors
        self.bidir_aligner = bidir_aligner

        self.expected_params = {}
        if slang:
            self.expected_params['source'] = slang.lower()
        if tlang:
            self.expected_params['target'] = tlang.lower()

        self.pretty = bool(pretty)
        self.timeout = timeout
        self.verbose = verbose

    def _check_params(self, params):
        errors = []
        missing = [p for p in self.required_params if not p in params]
        if missing:
            for p in missing:
                errors.append({"domain":"global",
                               "reason":"required",
                               "message":"Required parameter: %s" %p,
                               "locationType": "parameter",
                               "location": "%s" %p})
            return {"error": {"errors":errors,
                              "code":400,
                              "message":"Required parameter: %s" %missing[0]}}

        for key, val in self.expected_params.iteritems():
            assert key in params, "expected param %s" %key
            if params[key].lower() != val:
                message = "expetect value for parameter %s:'%s'" %(key,val)
                errors.append({"domain":"global",
                               "reason":"invalid value: '%s'" %params[key],
                               "message":message,
                               "locationType": "parameter",
                               "location": "%s" %p})
                return {"error": {"errors":errors,
                                  "code":400,
                                  "message":message}}
        return None

    def _timeout_error(self, q, location):
        errors = [{"originalquery":q, "location" : location}]
        message = "Timeout after %ss" %self.timeout
        return {"error": {"errors":errors, "code":400, "message":message}}

    def _getOnlyTranslation(self, query):
        re_align = re.compile(r'<passthrough[^>]*\/>')
        query = re_align.sub('',query)
        return query

    def _getAlignment(self, query, tagname):
        pattern = "<passthrough[^>]*"+tagname+"=\"(?P<align>[^\"]*)\"\/>"
        re_align = re.compile(pattern)
        m = re_align.search(query)
        if not m:
            return query, None

        query = re_align.sub('',query)
        alignment = m.group('align')
        alignment = re.sub(' ','',alignment)
        data = self._load_json('{"align": %s}' % alignment)

        return query, data["align"]

    def _getPhraseAlignment(self, query):
        return self._getAlignment(query, 'phrase_alignment')

    def _getWordAlignment(self, query):
        return self._getAlignment(query, 'word_alignment')

    def _dump_json(self, data):
        if self.pretty:
            return json.dumps(data, indent=2) + "\n"
        return json.dumps(data) + "\n"

    def _load_json(self, string):
        return json.loads(string)

    def _process_externally(self, q, processor, name):
        response = cherrypy.response
        response.headers['Content-Type'] = 'application/json'
        data = {"data" : {"translations" : [{name : processor(q)}]}}
        return self._dump_json(data)

    def _track_preprocessing(self, sentence, is_source, verbose=False):
        processors = self.external_processors if is_source else self.tgt_external_processors
        sentence_tokenized = processors.tokenize(sentence)
        sentence_truecased = processors.truecase(sentence_tokenized)
        sentence_preprocessed  = processors.prepro(sentence_truecased)
        tracker = tokentracker.TokenTracker()
        # tracker applied in opposite direction as final spans refer to input
        spans = tracker.track_detok(sentence_preprocessed, sentence_truecased, verbose=verbose)
        spans = tracker.track_detok(sentence_truecased, sentence_tokenized, spans=spans, verbose=verbose)
        spans = tracker.track_detok(sentence_tokenized, sentence, spans=spans, verbose=verbose, check_escape=True)
        return sentence_preprocessed, spans

    def _track_postprocessing(self, sentence, verbose=False):
        processors = self.external_processors
        tracker = tokentracker.TokenTracker()
        sentence_postprocessed  = processors.postpro(sentence)
        sentence_detruecased = processors.detruecase(sentence_postprocessed)
        sentence_detokenized = processors.detokenize(sentence_detruecased)
        spans = tracker.track_detok(sentence, sentence_postprocessed, verbose=verbose)
        spans = tracker.track_detok(sentence_postprocessed, sentence_detruecased, spans=spans, verbose=verbose)
        spans = tracker.track_detok(sentence_detruecased, sentence_detokenized, spans=spans, verbose=verbose, check_escape=True)
        return sentence_detokenized, spans

    @cherrypy.expose
    def tokenize(self, **kwargs):
        source = self.filter.filter(kwargs["q"])
        target = self.filter.filter(kwargs["t"])

        source_preprocessed, source_spans = self._track_preprocessing(source, is_source=True)
        target_preprocessed, target_spans = self._track_preprocessing(target, is_source=False)

        align_data = {'sourceText':source, 'targetText':target}
        align_data['tokenization'] = {'src': source_spans, 'tgt': target_spans}
        align_data['tokenizedTarget'] = target_preprocessed
        align_data['tokenizedSource'] = source_preprocessed
        data = {"data" : align_data}
        return self._dump_json(data)

    @cherrypy.expose
    def detokenize(self, **kwargs):
        q = self.filter.filter(kwargs["q"])
        return self._process_externally(q, self.external_processors.detokenize, 'detokenizedText')

    @cherrypy.expose
    def truecase(self, **kwargs):
        q = self.filter.filter(kwargs["q"])
        return self._process_externally(q, self.external_processors.truecase, 'truecasedText')

    @cherrypy.expose
    def detruecase(self, **kwargs):
        q = self.filter.filter(kwargs["q"])
        return self._process_externally(q, self.external_processors.detruecase, 'detruecasedText')

    @cherrypy.expose
    def prepro(self, **kwargs):
        q = self.filter.filter(kwargs["q"])
        return self._process_externally(q, self.external_processors.prepro, 'preprocessedText')

    @cherrypy.expose
    def postpro(self, **kwargs):
        q = self.filter.filter(kwargs["q"])
        return self._process_externally(q, self.external_processors.postpro, 'postprocessedText')

    def _translate(self, source, sg=False, align=False, topt=False, factors=False, nbest=0):
        """ wraps the actual translate call to mosesserver via XMLPRC """
        proxy = xmlrpclib.ServerProxy(self.moses_url)
        params = {"text":source}
        if align: params["align"] = "true"
        if sg: params["sg"] = "true"
        if topt: params["topt"] = "true"
        if factors: params["report-all-factors"] = "true"
        if nbest > 0: params["nbest"] = nbest
        return proxy.translate(params)

    def _update(self, source, target, alignment):
        """ wraps the actual update call to mosesserver via XMLPRC """
        proxy = xmlrpclib.ServerProxy(self.moses_url)
        params = {"source":source, "target":target, "alignment":alignment}
        return proxy.updater(params)

    def _getTranslation(self, hyp):
        """ does all the extraction and postprocessing, returns dict including
            translatedText, spans, and, if available, phraseAlignment,
            and WordAlignment
        """
        translationDict = {}
        translation = hyp.strip()

        self.log_info("Translation before extraction: %s" %translation)
        translation = self.external_processors.extract(translation)
        self.log_info("Translation after extraction: %s" %translation)

        translation, phraseAlignment = self._getPhraseAlignment(translation)
        self.log_info("Phrase alignment: %s" %str(phraseAlignment))
        self.log_info("Translation after removing phrase-alignment: %s" %translation)

        translation, wordAlignment = self._getWordAlignment(translation)
        self.log_info("Word alignment: %s" %str(wordAlignment))
        self.log_info("Translation after removing word-alignment: %s" %translation)

        translation = self._getOnlyTranslation(translation).strip()
        self.log_info("Translation after removing additional info: %s" %translation)

        self.log_info("Translation before postprocessing: %s" %translation)
        translationDict["translatedTextRaw"] = translation
        translation, spans = self._track_postprocessing(translation)
        if not "tokenization" in translationDict:
            translationDict["tokenization"] = {}
        translationDict["tokenization"].update( {'tgt' : spans} )
        self.log_info("Translation after postprocessing: %s" %translation)

        if translation:
            translationDict["translatedText"] = translation
        else:
            translationDict["translatedText"] = ''
        if phraseAlignment:
            translationDict["phraseAlignment"] = phraseAlignment
        if wordAlignment:
            translationDict["wordAlignment"] = wordAlignment

        return translationDict

    @cherrypy.expose
    def translate(self, **kwargs):
        response = cherrypy.response
        response.headers['Content-Type'] = 'application/json'

        errors = self._check_params(kwargs)
        if errors:
            cherrypy.response.status = 400
            return self._dump_json(errors)

        q = self.filter.filter(kwargs["q"])
        raw_src = q
        self.log("The server is working on: %s" %repr(raw_src))
        self.log_info("Request before preprocessing: %s" %repr(raw_src))
        translationDict = {"sourceText":raw_src.strip()}
        preprocessed_src, src_spans = self._track_preprocessing(raw_src,
                                                                is_source=True)
        self.log_info("Request after preprocessing: %s" %repr(preprocessed_src))
        self.log_info("Request before annotation: %s" %repr(q))
        annotated_src = self.external_processors.annotate(preprocessed_src)
        not_annotated_src = self._getOnlyTranslation(annotated_src)
        assert len(preprocessed_src.split()) == len(not_annotated_src.split()), \
                        "annotation should not change number of tokens"
        translationDict = {"annotatedSource":annotated_src}

        self.log_info("Request after annotation (q): %s" %repr(annotated_src))

        translation = ''
        report_search_graph = 'sg' in kwargs
        report_translation_options = 'topt' in kwargs
        report_alignment = 'align' in kwargs

        # how many -if any- entries do we need in the nbest list?
        nbest = 0
        if 'nbest' in kwargs:
            nbest = max(nbest, int(kwargs['nbest']))
        if 'wpp' in kwargs:
            nbest = max(nbest, int(kwargs['wpp']))

        # query MT engine
	print "requesting translation"
        result = self._translate(annotated_src,
                                 sg=report_search_graph,
                                 topt = report_translation_options,
                                 align = report_alignment,
                                 nbest = nbest)
	print "received translation"
        if 'text' in result:
            translation = result['text']
        else:
            return self._timeout_error(annotated_src, 'translation')
        translationDict.update(self._getTranslation(translation))
        translationDict["tokenization"].update( {'src' : src_spans} )

        if 'sg' in result:
            translationDict['searchGraph'] = result['sg']
        if 'topt' in result:
            translationDict['topt'] = result['topt']
        if 'align' in result:
            translationDict['alignment'] = result['align']
        if 'nbest' in result:
            if 'nbest' in kwargs:
                n = int(kwargs['nbest'])
                n = min(n, len(result['nbest']))
                translationDict['raw_nbest'] = result['nbest'][:n]
                translationDict['nbest'] = []
                for nbest_result in result['nbest'][:n]:
                    hyp = nbest_result['hyp']
                    translationDict['nbest'].append(self._getTranslation(hyp))
            if 'wpp' in kwargs:
                buff = []
                n = int(kwargs['wpp'])
                n = min(n, len(result['nbest']))
                for nbest_result in result['nbest'][:n]:
                    hyp = nbest_result['hyp']
                    score = nbest_result['totalScore']
                    buff.append( [0, hyp, score] )
                word_posterior = wpp.WPP(align=True)
                probs = word_posterior.process_buff(buff, translation)
                translationDict['wpp'] = map(math.exp, probs)
                translationDict['wpp_score'] = geometric_mean(probs)


        data = {"data" : {"translations" : [translationDict]}}
        self.log("The server is returning: %s" %self._dump_json(data))
        return self._dump_json(data)

    @cherrypy.expose
    def align(self, **kwargs):
        response = cherrypy.response
        response.headers['Content-Type'] = 'application/json'

        if self.bidir_aligner == None:
            message = "need bidirectional aligner for updates"
            return self._dump_json ({"error": {"code":400, "message":message}})

        source = self.filter.filter(kwargs["q"])
        target = self.filter.filter(kwargs["t"])

        print "Aligning: %s / %s" %(source.encode('utf8'),target.encode('utf8'))

        # pre-processing of source and target
        source_preprocessed, source_spans = self._track_preprocessing(source, is_source=True)
        target_preprocessed, target_spans = self._track_preprocessing(target, is_source=False)

        # set mode
        mode = 's2t'
        if 'mode' in kwargs:
            mode = self.filter.filter(kwargs["mode"])

	# aligner must exist
        if self.bidir_aligner == None:
            message = "need bidirectional aligner for updates"
            return self._dump_json ({"error": {"code":400, "message":message}})

	# return empty alignment matrix on failure
        alignment = ''

        if len(target_preprocessed) == 0 or len(source_preprocessed) == 0:
	    print "no target words... return no alignment points"
	    alignment = []
        elif mode == 's2t':
	    print "yep. %s / %s" %(source_preprocessed.encode('utf8'),target_preprocessed.encode('utf8'))
            alignment = self.bidir_aligner.s2t.align(source_preprocessed, target_preprocessed)
	    print "yep. %s" % alignment
            target_preprocessed = target_preprocessed.split()
            source_preprocessed = source_preprocessed.split()
            print alignment, target_preprocessed
	    print "len %s : %s" %(len(target_preprocessed), target_preprocessed)
	    print "len %s : %s" %(len(alignment), alignment)
            alignment_dict = []
            if len(target_preprocessed) == len(alignment):
              for tgt_idx, (a, tgt_word) in enumerate(zip(alignment, target_preprocessed)):
                if a != 0:
                    alignment_dict.append( {"src_idx": a-1,
                                            "tgt_idx": tgt_idx,
                                            "src_word": source_preprocessed[a-1],
                                            "tgt_word": target_preprocessed[tgt_idx]})
            alignment = alignment_dict
        elif mode == 't2s':
            alignment = self.bidir_aligner.t2s.align(target_preprocessed, source_preprocessed)
            target_preprocessed = target_preprocessed.split()
            source_preprocessed = source_preprocessed.split()

            assert len(source_preprocessed) == len(alignment)
            alignment_dict = []
            for src_idx, (a, src_word) in enumerate(zip(alignment, source_preprocessed)):
                if a != 0:
                    alignment_dict.append( {"tgt_idx": a-1,
                                            "src_idx": src_idx,
                                            "src_word": source_preprocessed[src_idx],
                                            "tgt_word": target_preprocessed[a-1]})
            alignment = alignment_dict

        elif mode == 'sym':
            a_s2t = self.bidir_aligner.s2t.align(source_preprocessed, target_preprocessed)
            a_t2s = self.bidir_aligner.t2s.align(target_preprocessed, source_preprocessed)
            alignment = self.bidir_aligner.symal.symmetrize(source_preprocessed, target_preprocessed, a_s2t, a_t2s)

            target_preprocessed = target_preprocessed.split()
            source_preprocessed = source_preprocessed.split()

            assert len(target_preprocessed) == len(a_s2t)
            assert len(source_preprocessed) == len(a_t2s)

            alignment_dict = []
            for src_idx, tgt_idx in alignment:
            #for tgt_idx, src_idx in alignment:
                alignment_dict.append( {"tgt_idx": tgt_idx,
                                        "src_idx": src_idx,
                                        "src_word": source_preprocessed[src_idx],
                                        "tgt_word": target_preprocessed[tgt_idx]})
            alignment = alignment_dict

            print "alignment afer symal:", alignment
        else:
            message = "unknown alignment mode %s" %mode
            return self._dump_json ({"error": {"code":400, "message":message}})
        #alignment = [point for point in alignment if point[0] != -1 and point[1] != -1]

        align_data = {'sourceText':source,
                      'targetText':target,
                      'alignment':alignment,
                      'tokenization': { 'src': source_spans, 'tgt': target_spans }
                     }
        data = {"data" : align_data}
        return self._dump_json(data)

    @cherrypy.expose
    def update(self, source, target, q, t):
        if self.bidir_aligner == None:
            message = "need bidirectional aligner for updates"
            return self._dump_json ({"error": {"code":400, "message":message}})

        segment_preprocessed, segment_spans = self._track_preprocessing(q, is_source=True)
        translation_preprocessed, translation_spans = self._track_preprocessing(t, is_source=False)

        if len(segment_preprocessed) == 0 or len(translation_preprocessed) == 0:
            message = "segment or translation is empty - rejected"
            return self._dump_json ({"error": {"code":400, "message":message}})

        if len(segment_preprocessed) * 4 < len(translation_preprocessed) or len(segment_preprocessed) > 4 * len(translation_preprocessed):
            message = "length mismatch - rejected"
            return self._dump_json ({"error": {"code":400, "message":message}})

        a_s2t = self.bidir_aligner.s2t.align(segment_preprocessed, translation_preprocessed)
        a_t2s = self.bidir_aligner.t2s.align(translation_preprocessed, segment_preprocessed)
        assert len(translation_preprocessed.split()) == len(a_s2t)
        assert len(segment_preprocessed.split()) == len(a_t2s)

        print "E";
        alignment = self.bidir_aligner.symal.symmetrize(segment_preprocessed, translation_preprocessed, a_s2t, a_t2s)
        print "F";
        alignment_strings = []
        for src_idx, tgt_idx in alignment:
            alignment_strings.append( "%d-%d" %(src_idx, tgt_idx) )
        print "G %s" % alignment_strings;

        self.log("Updating model with src: %s tgt: %s, align: %s" \
                 %(segment_preprocessed.encode('utf8'),
                   translation_preprocessed.encode('utf8'),
                   " ".join(alignment_strings)))
        print "H";

        self._update(segment_preprocessed, translation_preprocessed, " ".join(alignment_strings))
        update_dict = {'segment':segment_preprocessed, 'translation':translation_preprocessed, 'alignment':alignment}
        data = {"data" : {"update" : [update_dict]}}
        return self._dump_json(data)

    def log_info(self, message):
        if self.verbose > 0:
            self.log(message, level=logging.INFO)

    def log(self, message, level=logging.INFO):
        logger = logging.getLogger('translation_log.info')
        logger.info(message)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-ip', help='server ip to bind to, default: localhost', default="127.0.0.1")
    parser.add_argument('-port', action='store', help='server port to bind to, default: 8080', type=int, default=8080)
    parser.add_argument('-nthreads', help='number of server threads, default: 8', type=int, default=8)
    #parser.add_argument('-moses', dest="moses_path", action='store', help='path to moses executable', required=True)
    #parser.add_argument('-options', dest="moses_options", action='store', help='moses options, including .ini -async-output -print-id', required=True)

    parser.add_argument('-mosesurl', dest="moses_url", action='store', help='url of mosesserver', required=True)
    parser.add_argument('-timeout', help='timeout for call to translation engine, default: unlimited', type=int)

    parser.add_argument('-tokenizer', nargs="+", help='call to tokenizer, including arguments, PREPROSTEP(S) 1', default=[])
    parser.add_argument('-truecaser', nargs="+", help='call to truecaser, including arguments, PREPROSTEP(S) 2', default=[])
    parser.add_argument('-prepro', nargs="+", help='complete call to preprocessing script(s) including arguments, PREPROSTEP(S) 3', default=[])
    parser.add_argument('-annotators', nargs="+", help='call to scripts run AFTER prepro, before translation, PREPROSTEP(S) 4', default=[])
    parser.add_argument('-extractors', nargs="+", help='call to scripts run BEFORE postpro, after translation', default=[])
    parser.add_argument('-postpro', nargs="+", help='complete call to postprocessing script(s) including arguments, run before detruecaser', default=[])
    parser.add_argument('-detruecaser', nargs='+', help='call to detruecaser, including arguments', default=[])
    parser.add_argument('-detokenizer', nargs='+', help='call to detokenizer, including arguments', default=[])

    parser.add_argument('-tgt-tokenizer', nargs="+", dest="tgt_tokenizer", help='call to target tokenizer, including arguments, PREPROSTEP(S) 1', default=[])
    parser.add_argument('-tgt-truecaser', nargs="+", dest="tgt_truecaser", help='call to target truecaser, including arguments, PREPROSTEP(S) 2', default=[])
    parser.add_argument('-tgt-prepro', nargs="+", dest="tgt_prepro", help='complete call to target preprocessing script(s) including arguments, PREPROSTEP(S) 3', default=[])

    # Options concerning Confidences
    #parser.add_argument('-wpp-n', dest='wpp_n', help="length of nbest list to compute wpps from")

    # Options to run the Bidirectional Aligner for Online Adaptation
    #parser.add_argument('-s2t-hmm', dest='s2t_hmm', help="HMM transition probs from GIZA++")
    #parser.add_argument('-s2t-lex', dest='s2t_lex', help="translation probs p(src|tgt)")
    #parser.add_argument('-t2s-hmm', dest='t2s_hmm', help="HMM transition probs from GIZA++")
    #parser.add_argument('-t2s-lex', dest='t2s_lex', help="translation probs p(tgt|src)")
    #parser.add_argument('-sourcevoc', help="source vocabulary")
    #parser.add_argument('-targetvoc', help="target vocabulary")
    #parser.add_argument('-pnull', type=float, help="jump probability to/from NULL word (default: 0.4)", default=0.4)
    #parser.add_argument('-minp', help='minimal translation probability, used to prune the model', default=0.0, type=float)
    parser.add_argument('-symal', help="path to symal, including arguments")
    parser.add_argument('-omgiza_src2tgt', help='path of online-MGiza++, including arguments for src-tgt alignment')
    parser.add_argument('-omgiza_tgt2src', help='path of online-MGiza++, including arguments for tgt-src alignment')

    parser.add_argument('-pretty', action='store_true', help='pretty print json')
    parser.add_argument('-slang', help='source language code')
    parser.add_argument('-tlang', help='target language code')
    #parser.add_argument('-log', choices=['DEBUG', 'INFO'], help='logging level, default:DEBUG', default='DEBUG')
    parser.add_argument('-logprefix', help='logfile prefix, default: write to stderr')
    parser.add_argument('-verbose', help='verbosity level, default: 0', type=int, default=0)
    # persistent threads
    thread_options = parser.add_mutually_exclusive_group()
    thread_options.add_argument('-persist', action='store_true', help='keep pre/postprocessing scripts running')
    thread_options.add_argument('-nopersist', action='store_true', help='don\'t keep pre/postprocessing scripts running')

    args = parser.parse_args(sys.argv[1:])
    persistent_processes = not args.nopersist

    if args.logprefix:
        init_log("%s.trans.log" %args.logprefix)

    sys.stderr.write("loading external source processors ...\n")
    external_processors = ExternalProcessors(args.tokenizer, args.truecaser,
                                          args.prepro, args.annotators,
                                          args.extractors, args.postpro,
                                          args.detruecaser, args.detokenizer)

    sys.stderr.write("loading external target processors ...\n")
    tgt_external_processors = ExternalProcessors(args.tgt_tokenizer,
                                                 args.tgt_truecaser,
                                                 args.tgt_prepro,
                                                 [], [], [], [], [])

    # online MGiza++ processes for alignment
    giza_s2t = mgiza.OnlineMGiza(args.omgiza_src2tgt) if args.omgiza_src2tgt else None
    giza_t2s = mgiza.OnlineMGiza(args.omgiza_tgt2src) if args.omgiza_tgt2src else None
    symal_wrapper = symal.SymalWrapper(args.symal) if args.symal else None
    bidir_aligner = aligner.BidirectionalAligner(giza_s2t, giza_t2s, symal_wrapper)

    cherrypy.config.update({'server.request_queue_size' : 1000,
                            'server.socket_port': args.port,
                            'server.thread_pool': args.nthreads,
                            'server.socket_host': args.ip})
    cherrypy.config.update({'error_page.default': json_error})
    cherrypy.config.update({'log.screen': True})
    if args.logprefix:
        cherrypy.config.update({'log.access_file': "%s.access.log" %args.logprefix,
                                'log.error_file': "%s.error.log" %args.logprefix})
    cherrypy.quickstart(Root(args.moses_url,
                             external_processors = external_processors,
                             tgt_external_processors = tgt_external_processors,
                             bidir_aligner = bidir_aligner,
                             slang = args.slang, tlang = args.tlang,
                             pretty = args.pretty,
                             verbose = args.verbose))
