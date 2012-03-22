#!/usr/bin/python -u
import sys
import Queue
import threading
import subprocess
import cherrypy
import simplejson


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
                    q.put(line[1])
                    result_queues.pop(idx)
                    found = True
                    break
            assert found, "id %s not found!\n" %(line[0])

class MosesProc(object):
    def __init__(self, cmd):
        cmd = cmd.split()
        sys.stderr.write("executing: %s\n" %(" ".join(cmd)))
        self.proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE)

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

class Root(object):
    def __init__(self, queue):
        self.queue = queue

    @cherrypy.expose
    def translate(self, q):
        print q
        result_queue = Queue.Queue()
        self.queue.put((result_queue, "%s\n" %(q)))
        response = cherrypy.response
        response.headers['Content-Type'] = 'application/json'

        translation = result_queue.get()
        return simplejson.dumps({"translation" : translation})

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-ip', action='store', help='server ip to bind to, default: localhost', default="127.0.0.1")
    parser.add_argument('-port', action='store', help='server port to bind to, default: 8080', type=int, default=8080)
    parser.add_argument('-nthreads', action='store', help='number of server threads, default: 10', type=int, default=8)
    parser.add_argument('-moses', dest="moses_path", action='store', help='path to moses executable', default="/home/buck/src/mosesdecoder/moses-cmd/src/moses")
    parser.add_argument('-options', dest="moses_options", action='store', help='moses options, including .ini -async-output -print-id', default="-f phrase-model/moses.ini -v 0 -threads 2 -async-output -print-id")
    args = parser.parse_args(sys.argv[1:])

    moses = MosesProc(" ".join((args.moses_path, args.moses_options)))

    cherrypy.config.update({'server.request_queue_size' : 1000,
                            'server.socket_port': args.port,
                            'server.thread_pool': args.nthreads,
                            'server.socket_host': args.ip})
    cherrypy.quickstart(Root(moses.source_queue))

    moses.close()
