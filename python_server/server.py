#!/usr/bin/python -u
import sys
import threading
import subprocess
import cherrypy
import json
import logging
import re
import xmlrpclib
import math
from threading import Timer
from aligner import hmmalign
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
        return result.decode("utf-8").rstrip()

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
        self.symal = bidir_aligner

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

    @cherrypy.expose
    def tokenize(self, q):
        #q = self.filter.filter(kwargs["q"])
        return self._process_externally(q, self.external_processors.tokenize, 'tokenizedText')

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
        #params = {"text":source, "align":"true", "report-all-factors":"false"}
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
        tt = tokentracker.TokenTracker()
        raw_translation = translation
        spans = tt.tokenize(raw_translation)
        translation = self.external_processors.postpro(translation)
        spans = tt.track_detok(raw_translation, translation, spans)
        raw_translation = translation
        translation = self.external_processors.detruecase(translation)
        spans = tt.track_detok(raw_translation, translation, spans)
        raw_translation = translation
        translation = self.external_processors.detokenize(translation)
        spans = tt.track_detok(raw_translation, translation, spans)
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
        self.log("The server is working on: %s" %repr(q))
        self.log_info("Request before preprocessing: %s" %repr(q))
        translationDict = {"sourceText":q.strip()}
        q = self.external_processors.tokenize(q)
        q = self.external_processors.truecase(q)
        q = self.external_processors.prepro(q)

        self.log_info("Request after preprocessing: %s" %repr(q))
        preprocessed_src = q
        tt = tokentracker.TokenTracker()
        src_spans = tt.tokenize(preprocessed_src)
        src_spans = tt.track_detok(preprocessed_src, raw_src, src_spans)

        self.log_info("Request before annotation: %s" %repr(q))
        q = self.external_processors.annotate(q)
        assert len(preprocessed_src.split()) == len(q.split()), \
                        "annotation should not change number of tokens"

        self.log_info("Request after annotation: %s" %repr(q))

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

        result = self._translate(q, sg=report_search_graph,
                                 topt = report_translation_options,
                                 align = report_alignment,
                                 nbest = nbest)
        if 'text' in result:
            translation = result['text']
        else:
            return self._timeout_error(q, 'translation')
        #print result.keys()
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


        data = {"data" : {"translations" : [translationDict]}}
        self.log("The server is returning: %s" %self._dump_json(data))
        return self._dump_json(data)

    @cherrypy.expose
    def align(self, source, target, mode):
        if self.symal == None:
            message = "need bidirectional aligner for updates"
            return {"error": {"code":400, "message":message}}
        source = self.external_processors.tokenize(source)
        source = self.external_processors.truecase(source)
        source = self.external_processors.prepro(source)

        target = self.tgt_external_processors.tokenize(target)
        target = self.tgt_external_processors.truecase(target)
        target = self.tgt_external_processors.prepro(target)

        if self.symal == None:
            message = "need bidirectional aligner for updates"
            return {"error": {"code":400, "message":message}}
        alignment = ''
        if mode == 's2t':
            alignment = self.symal.align_s2t(source, target)
            alignment = " ".join(["%s-%s" %(j,i) for j,i in alignment])
        elif mode == 't2f':
            alignment = self.symal.align_t2s(source, target)
            alignment = " ".join(["%s-%s" %(i,j) for i,j in alignment])
        elif mode == 'sym':
            pass
        else:
            message = "unknow alignment mode %s" %mode
            return {"error": {"code":400, "message":message}}
        align_dict = {'source':source, 'target':target, 'alignment':alignment}
        data = {"data" : {"alignment" : [align_dict]}}
        return self._dump_json(data)

    @cherrypy.expose
    def update(self, source, target, segment, translation):
        if self.symal == None:
            message = "need bidirectional aligner for updates"
            return {"error": {"code":400, "message":message}}

        #source_lang = source
        #target_lang = target

        segment = self.external_processors.tokenize(segment)
        segment = self.external_processors.truecase(segment)
        segment = self.external_processors.prepro(segment)

        translation = self.tgt_external_processors.tokenize(translation)
        translation = self.tgt_external_processors.truecase(translation)
        translation = self.tgt_external_processors.prepro(translation)

        alignment = self.symal.symal(segment, translation)

        self.log("Updating model with src: %s tgt: %s, align: %s" %(segment,
                                                                    translation,
                                                                    alignment))
        self._update(segment, translation, alignment)
        update_dict = {'segment':segment, 'translation':translation, 'alignment':alignment}
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
    parser.add_argument('-s2t-hmm', dest='s2t_hmm', help="HMM transition probs from GIZA++")
    parser.add_argument('-s2t-lex', dest='s2t_lex', help="translation probs p(src|tgt)")
    parser.add_argument('-t2s-hmm', dest='t2s_hmm', help="HMM transition probs from GIZA++")
    parser.add_argument('-t2s-lex', dest='t2s_lex', help="translation probs p(tgt|src)")
    parser.add_argument('-sourcevoc', help="source vocabulary")
    parser.add_argument('-targetvoc', help="target vocabulary")
    parser.add_argument('-symal', help="path to symal, including arguments")
    parser.add_argument('-pnull', type=float, help="jump probability to/from NULL word (default: 0.4)", default=0.4)
    parser.add_argument('-minp', help='minimal translation probability, used to prune the model', default=0.0, type=float)

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

    ba = None
    if args.s2t_hmm and args.s2t_lex and args.t2s_hmm and args.t2s_lex \
        and args.sourcevoc and args.targetvoc and args.symal:
        sys.stderr.write("loading bidirectional aligner...\n")
        ba = hmmalign.BidirectionalAligner(args.sourcevoc, args.targetvoc,
                                           args.s2t_hmm, args.s2t_lex,
                                           args.t2s_hmm, args.t2s_lex,
                                           args.minp, args.pnull,
                                           symal = args.symal)

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
                             bidir_aligner = ba,
                             slang = args.slang, tlang = args.tlang,
                             pretty = args.pretty,
                             verbose = args.verbose))
