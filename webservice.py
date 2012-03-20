#!/usr/bin/python -u
import sys
import cherrypy
import Queue
import threading
import subprocess

class WriteThread(threading.Thread):
    def __init__(self, moses_in, source_queue):
        threading.Thread.__init__(self)
        self.mosespipe = moses_in
        self.source_queue = source_queue

    def run(self):
        while True:
            # blocking read
            source = self.source_queue.get()
            # blocking write
            self.mosespipe.write(source)
            self.source_queue.task_done()

class ReadThread(threading.Thread):
    def __init__(self, moses_out, target_queue):
        threading.Thread.__init__(self)
        self.mosespipe = moses_out
        self.target_queue = target_queue

    def run(self):
        while True:
            line = self.mosespipe.readline()
            if not line:
                break
            self.target_queue.put(line)
            print line
            self.target_queue.task_done()


class Root(object):
    def __init__(self):
        pass

    @cherrypy.expose
    def translate(self, q):
        print q
        response = cherrypy.response
        response.headers['Content-Type'] = 'application/json'
        return self.__predict_json(data)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-ip', action='store', help='server ip to bind to, default: localhost', default="127.0.0.1")
    parser.add_argument('-port', action='store', help='server port to bind to, default: 8080', type=int, default=8080)
    parser.add_argument('-nthreads', action='store', help='number of server threads, default: 10', type=int, default=8)
    args = parser.parse_args(sys.argv[1:])

    moses_cmd = "/home/buck/src/matecat/shuffleline.py"
    moses = subprocess.Popen(moses_cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE)

    source_queue = Queue.Queue()
    target_queue = Queue.Queue()

    writer = WriteThread(moses.stdin, source_queue)
    writer.setDaemon(True)
    writer.start()

    reader = ReadThread(moses.stdout, target_queue)
    #reader.setDaemon(True)
    reader.start()

    for i in range(8):
        source_queue.put("string %s\n" %i)

    source_queue.put("")

    print "source_queue: ", source_queue.empty()
    print "target_queue: ", target_queue.empty()

    source_queue.join()

    # call this function when a thread is created
    #def init_thread(thread_index):
    #    pass
    #    # cherrypy.thread_data.out_queue
    #cherrypy.engine.subscribe('start_thread', init_thread)
    #
    #cherrypy.config.update({'server.request_queue_size' : 1000,
    #                        'server.socket_port': args.port,
    #                        'server.thread_pool': args.nthreads,
    #                        'server.socket_host': args.ip})
    #cherrypy.quickstart(Root())

