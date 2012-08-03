#!/usr/bin/python

import os
from time import sleep
from random import randint
import sys
import codecs
import urllib
import urllib2
import json
from multiprocessing import Pool

def f(x):
    sleep(randint(0,4))
    return x*x


def get_translation_from_json(d):
    """ extract translation from a parsed json object
    d = Responses looking like this:
    {
      "data": {
        "translations": [
          {
            "translatedText": "food to Blame for European inflation"
          }
        ]
      }
    }
    """
    assert 'data' in d
    assert 'translations' in d['data']
    assert len(d['data']['translations']) == 1
    assert 'translatedText' in d['data']['translations'][0]
    return d['data']['translations'][0]['translatedText']

def query_server(query):
    response = urllib2.urlopen(query)
    response_data = json.load(response)
    translation = get_translation_from_json(response_data)
    return translation

def wrap_query(url_template, line):
    line = urllib.quote(line.encode('utf-8').strip())
    url = url_template %line
    return url


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-source', help='source data, default: read from stdin')
    parser.add_argument('-out', help='output file, default: write to stdout')
    parser.add_argument('-server', help='server address, default: localhost', default="127.0.0.1")
    parser.add_argument('-port', help='server port, default: 8080', type=int, default=8080)
    parser.add_argument('-nthreads', help='number of threads, default: 10', type=int, default=10)
    parser.add_argument('-maxlines', help='max number of lines to test, default: all', type=int)
    parser.add_argument('-slang', action='store', help='source language code', required=True)
    parser.add_argument('-tlang', action='store', help='target language code', required=True)
    parser.add_argument('-verbose', action='store_true', help='verbose mode')

    args = parser.parse_args(sys.argv[1:])


    #pool = Pool(processes=50)
    #result = pool.apply_async(f, range(100))
    #print result.get(timeout=1)
    #print pool.map(f, range(50))

    pool = Pool(processes=args.nthreads)

    url_template = "http://%s:%s" %(args.server, args.port) + \
                   "/translate?q=%s&key=0&"+ \
                   "target=%s&source=%s" %(args.tlang, args.slang)

    source_data = []
    if args.source:
        source_data = codecs.open(args.source,'r','utf-8').readlines()
    source_data = [s.decode('utf-8') for s in sys.stdin]

    maxlines = len(source_data)
    if args.maxlines:
        maxlines = min(args.maxlines, len(source_data))

    queries = (wrap_query(url_template, s) for s in source_data[:maxlines])

    if args.verbose:
        sys.stderr.write("loaded %s sentences\n" %(len(source_data)))
        sys.stderr.write("processing %s queries  in %s threads...\n"
                         %(args.nthreads, maxlines))

    translations = pool.map(query_server, queries)

    sys.exit()
    for line in sourcefile[:100]:
        line = urllib.quote(line.encode('utf-8').strip())
        url = "http://localhost:8080/translate?q=%s&key=0&target=en&source=de" %line
        response = urllib2.urlopen(url)
        response_data = json.load(response)
        #print json.dumps(response_data,indent=2)
        translation = get_translation_from_json(response_data)
        print translation
