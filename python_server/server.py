#!/usr/bin/python -u
import sys
import Queue
import threading
import subprocess
import cherrypy
import json

def popen(cmd):
    cmd = cmd.split()
    sys.stderr.write("executing: %s\n" %(" ".join(cmd)))
    return subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE)

class WriteThread(threading.Thread):
    def __init__(self, p_in, source_queue, web_queue):
        threading.Thread.__init__(self)
        self.pipe = p_in
        self.source_queue = source_queue
        self.web_queue = web_queue

    def run(self):
        id = 0
        while True:
            result_queue, source = self.source_queue.get()
            self.web_queue.put( (id, result_queue) )
            print "writing to process: ", repr(source)
            self.pipe.write(source)
            self.pipe.flush()
            id += 1
            self.source_queue.task_done()

class ReadThread(threading.Thread):
    def __init__(self, p_out, target_queue, web_queue):
        threading.Thread.__init__(self)
        self.pipe = p_out
        self.target_queue = target_queue
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
            line = line.rstrip().split(" ", 1)
            print "reader read: ", repr(line)

            found = False
            for idx, (id, q) in enumerate(result_queues):
                print id, line[0]
                if id == int(line[0]):
                    if len(line) > 1:
                        q.put(line[1])
                    else:
                        q.put("")
                    result_queues.pop(idx)
                    found = True
                    break
            assert found, "id %s not found!\n" %(line[0])

class MosesProc(object):
    def __init__(self, cmd):
        self.proc = popen(cmd)

        self.source_queue = Queue.Queue()
        self.target_queue = Queue.PriorityQueue()
        self.web_queue = Queue.Queue()

        self.writer = WriteThread(self.proc.stdin, self.source_queue, self.web_queue)
        self.writer.setDaemon(True)
        self.writer.start()

        self.reader = ReadThread(self.proc.stdout, self.target_queue, self.web_queue)
        self.reader.setDaemon(True)
        self. reader.start()

    def close(self):
        self.source_queue.join() # wait until all items in source_queue are processed
        self.proc.stdin.close()
        self.proc.wait()
        print "source_queue empty: ", self.source_queue.empty()
        print "target_queue empty: ", self.target_queue.empty()


def json_error(status, message, traceback, version):
    err = {"status":status, "message":message, "traceback":traceback, "version":version}
    return json.dumps(err, sort_keys=True, indent=4)

class Root(object):
    required_params = ["q", "key", "target", "source"]

    def __init__(self, queue, prepro_cmd=None, postpro_cmd=None):
        print prepro_cmd
        self.queue = queue
        self.prepro_cmd = []
        if prepro_cmd != None:
            self.prepro_cmd = prepro_cmd
        self.postpro_cmd = []
        if postpro_cmd != None:
            self.postpro_cmd = postpro_cmd

    def _check_params(self, params):
        errors = []
        missing = [p for p in self.required_params if not p in params]
        for p in missing:
            errors.append({"domain":"global","reason":"required","message":
                "Required parameter: %s" %p, "locationType": "parameter",
                "location": "%s" %p})
        if errors:
            return {"error": {"errors":errors,
                              "code": 400,
                              "message": "Required parameter: %s" %missing[0]}}
        return None

    def _pipe(self, proc, s):
        proc.stdin.write("%s\n" %s)
        proc.stdin.flush()
        return proc.stdout.readline().rstrip()

    def _prepro(self, query):
        if not hasattr(cherrypy.thread_data, 'prepro'):
            cherrypy.thread_data.prepro = map(popen, self.prepro_cmd)
        for proc in cherrypy.thread_data.prepro:
            query = self._pipe(proc, query)
        return query

    def _postpro(self, query):
        if not hasattr(cherrypy.thread_data, 'postpro'):
            cherrypy.thread_data.postpro = map(popen, self.postpro_cmd)
        for proc in cherrypy.thread_data.postpro:
            query = self._pipe(proc, query)
        return query

    @cherrypy.expose
    def translate(self, **kwargs):
        errors = self._check_params(kwargs)
        if errors:
            cherrypy.response.status = 400
            return json.dumps(errors, sort_keys=True, indent=4)
        q = self._prepro(kwargs["q"])
        result_queue = Queue.Queue()
        self.queue.put((result_queue, "%s\n" %(q)))
        response = cherrypy.response
        response.headers['Content-Type'] = 'application/json'
        translation = result_queue.get()
        translation = self._postpro(translation)
        data = {"data" : {"translations" : [{"translatedText":translation}]}}

        return json.dumps(data)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-ip', action='store', help='server ip to bind to, default: localhost', default="127.0.0.1")
    parser.add_argument('-port', action='store', help='server port to bind to, default: 8080', type=int, default=8080)
    parser.add_argument('-nthreads', action='store', help='number of server threads, default: 8', type=int, default=8)
    parser.add_argument('-moses', dest="moses_path", action='store', help='path to moses executable', default="/home/buck/src/mosesdecoder/moses-cmd/src/moses")
    parser.add_argument('-options', dest="moses_options", action='store', help='moses options, including .ini -async-output -print-id', default="-f phrase-model/moses.ini -v 0 -threads 2 -async-output -print-id")
    parser.add_argument('-prepro', action='store', nargs="+", help='complete call to preprocessing script including arguments')
    parser.add_argument('-postpro', action='store', nargs="+", help='complete call to postprocessing script including arguments')
    args = parser.parse_args(sys.argv[1:])

    moses = MosesProc(" ".join((args.moses_path, args.moses_options)))

    cherrypy.config.update({'server.request_queue_size' : 1000,
                            'server.socket_port': args.port,
                            'server.thread_pool': args.nthreads,
                            'server.socket_host': args.ip})
    cherrypy.config.update({'error_page.default': json_error})
    cherrypy.quickstart(Root(moses.source_queue, args.prepro, args.postpro))

    moses.close()
