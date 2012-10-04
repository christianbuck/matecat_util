#!/usr/bin/python -u
import sys
import Queue
import threading
import subprocess
import cherrypy
import json
import logging
import re
from itertools import izip
from threading import Timer

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

class WriteThread(threading.Thread):
    def __init__(self, p_in, source_queue, web_queue):
        threading.Thread.__init__(self)
        self.pipe = p_in
        self.source_queue = source_queue
        self.web_queue = web_queue

    def run(self):
        i = 0
        while True:
            result_queue, source = self.source_queue.get()
            self.web_queue.put( (i, result_queue) )
            wrapped_src = u"<seg id=%s>%s</seg>\n" %(i, source)
            self.log("writing to process: %s" %repr(wrapped_src))
            self.pipe.write(wrapped_src.encode("utf-8"))
            self.pipe.flush()
            i += 1
            self.source_queue.task_done()

    def log(self, message):
        logger = logging.getLogger('translation_log.writer')
        logger.info(message)

class ReadThread(threading.Thread):
    def __init__(self, p_out, web_queue):
        threading.Thread.__init__(self)
        self.pipe = p_out
        self.web_queue = web_queue

    def run(self):
        result_queues = []
        while True:
            line = self.pipe.readline() # blocking read
            while not self.web_queue.empty():
                result_queues.append(self.web_queue.get())
            if line == '':
                assert self.web_queue.empty(), "still waiting for answers\n"
                assert result_queues, "unanswered requests\n"
                return
            line = line.decode("utf-8").rstrip().split(" ", 1)
            self.log("reader read: %s" %repr(line))

            found = False
            self.log("looking for id %s in %s result queues" %(line[0], len(result_queues)))
            for idx, (i, q) in enumerate(result_queues):
                if i == int(line[0]):
                    if len(line) > 1:
                        q.put(line[1])
                    else:
                        q.put("")
                    result_queues.pop(idx)
                    found = True
                    break
            assert found, "id %s not found!\n" %(line[0])

    def log(self, message):
        logger = logging.getLogger('translation_log.reader')
        logger.info(message)

class MosesProc(object):
    def __init__(self, cmd):
        self.proc = popen(cmd)

        self.source_queue = Queue.Queue()
        self.web_queue = Queue.Queue()

        self.writer = WriteThread(self.proc.stdin, self.source_queue, self.web_queue)
        self.writer.setDaemon(True)
        self.writer.start()

        self.reader = ReadThread(self.proc.stdout, self.web_queue)
        self.reader.setDaemon(True)
        self.reader.start()

    def close(self):
        self.source_queue.join() # wait until all items in source_queue are processed
        self.proc.stdin.close()
        self.proc.wait()
        self.log("source_queue empty: %s" %self.source_queue.empty())

    def log(self, message):
        logger = logging.getLogger('translation_log.moses')
        logger.info(message)

def json_error(status, message, traceback, version):
    err = {"status":status, "message":message, "traceback":traceback, "version":version}
    return json.dumps(err, sort_keys=True, indent=4)

class Root(object):
    required_params = ["q", "key", "target", "source"]

    def __init__(self, queue, prepro_cmd=None, postpro_cmd=None, slang=None,
                 tlang=None, pretty=False, persistent_processes=False,
                 timeout=-1):
        self.filter = Filter(remove_newlines=True, collapse_spaces=True)
        self.queue = queue
        self.prepro_cmd = []
        if prepro_cmd != None:
            self.prepro_cmd = prepro_cmd
        self.postpro_cmd = []
        if postpro_cmd != None:
            self.postpro_cmd = postpro_cmd
        self.expected_params = {}
        if slang:
            self.expected_params['source'] = slang.lower()
        if tlang:
            self.expected_params['target'] = tlang.lower()
        self.persist = bool(persistent_processes)
        self.pretty = bool(pretty)
        self.timeout = timeout

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

    def _pipe(self, proc, s):
        u_string = u"%s\n" %s
        proc.stdin.write(u_string.encode("utf-8"))
        proc.stdin.flush()
        return proc.stdout.readline().decode("utf-8").rstrip()
        #self.log("done.")

    def _prepro(self, query):
        if not self.persist or not hasattr(cherrypy.thread_data, 'prepro'):
            if hasattr(cherrypy.thread_data, 'prepro'):
                map(pclose, cherrypy.thread_data.prepro)
            cherrypy.thread_data.prepro = map(popen, self.prepro_cmd)
        for proc, cmd in izip(cherrypy.thread_data.prepro, self.prepro_cmd):
            query = self._pipe(proc, query)
        return query

    def _postpro(self, query):
        if not self.persist or not hasattr(cherrypy.thread_data, 'postpro'):
            if hasattr(cherrypy.thread_data, 'postpro'):
                map(pclose, cherrypy.thread_data.postpro)
            cherrypy.thread_data.postpro = map(popen, self.postpro_cmd)
        for proc in cherrypy.thread_data.postpro:
            query = self._pipe(proc, query)
        return query

    def _dump_json(self, data):
        if self.pretty:
            return json.dumps(data, indent=2) + "\n"
        return json.dumps(data) + "\n"

    @cherrypy.expose
    def translate(self, **kwargs):
        response = cherrypy.response
        response.headers['Content-Type'] = 'application/json'

        errors = self._check_params(kwargs)
        if errors:
            cherrypy.response.status = 400
            return self._dump_json(errors)
        self.log("Request before preprocessing: %s" %repr(kwargs["q"]))
        q = self._prepro(self.filter.filter(kwargs["q"]))
        self.log("Request after preprocessing: %s" %repr(q))
        translation = ""
        if q.strip():
            result_queue = Queue.Queue()
            self.queue.put((result_queue, q))
            try:
                if self.timeout and self.timeout > 0:
                    translation = result_queue.get(timeout=self.timeout)
                else:
                    translation = result_queue.get()
            except Queue.Empty:
                return self._timeout_error(q, 'translation')

        self.log("Translation before postprocessing: %s" %translation)
        translation = self._postpro(translation)
        self.log("Translation after postprocessing: %s" %translation)
        data = {"data" : {"translations" : [{"translatedText":translation}]}}
        return self._dump_json(data)

    def log(self, message):
        logger = logging.getLogger('translation_log')
        logger.info(message)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-ip', help='server ip to bind to, default: localhost', default="127.0.0.1")
    parser.add_argument('-port', action='store', help='server port to bind to, default: 8080', type=int, default=8080)
    parser.add_argument('-nthreads', help='number of server threads, default: 8', type=int, default=8)
    parser.add_argument('-moses', dest="moses_path", action='store', help='path to moses executable', default="/home/buck/src/mosesdecoder/moses-cmd/src/moses")
    parser.add_argument('-options', dest="moses_options", action='store', help='moses options, including .ini -async-output -print-id', default="-f phrase-model/moses.ini -v 0 -threads 2 -async-output -print-id")
    parser.add_argument('-prepro', nargs="+", help='complete call to preprocessing script including arguments')
    parser.add_argument('-postpro', nargs="+", help='complete call to postprocessing script including arguments')
    parser.add_argument('-pretty', action='store_true', help='pretty print json')
    parser.add_argument('-slang', help='source language code')
    parser.add_argument('-tlang', help='target language code')
    #parser.add_argument('-log', choices=['DEBUG', 'INFO'], help='logging level, default:DEBUG', default='DEBUG')
    parser.add_argument('-logprefix', help='logfile prefix, default: write to stderr')
    parser.add_argument('-timeout', help='timeout for call to translation engine, default: unlimited', type=int)
    # persistent threads
    thread_options = parser.add_mutually_exclusive_group()
    thread_options.add_argument('-persist', action='store_true', help='keep pre/postprocessing scripts running')
    thread_options.add_argument('-nopersist', action='store_true', help='don\'t keep pre/postprocessing scripts running')

    args = parser.parse_args(sys.argv[1:])
    persistent_processes = not args.nopersist

    if args.logprefix:
        init_log("%s.trans.log" %args.logprefix)

    moses = MosesProc(" ".join((args.moses_path, args.moses_options)))

    cherrypy.config.update({'server.request_queue_size' : 1000,
                            'server.socket_port': args.port,
                            'server.thread_pool': args.nthreads,
                            'server.socket_host': args.ip})
    cherrypy.config.update({'error_page.default': json_error})
    cherrypy.config.update({'log.screen': True})
    if args.logprefix:
        cherrypy.config.update({'log.access_file': "%s.access.log" %args.logprefix,
                                'log.error_file': "%s.error.log" %args.logprefix})
    cherrypy.quickstart(Root(moses.source_queue,
                             prepro_cmd = args.prepro, postpro_cmd = args.postpro,
                             slang = args.slang, tlang = args.tlang,
                             pretty = args.pretty,
                             persistent_processes = persistent_processes))

    moses.close()
