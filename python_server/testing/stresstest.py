#!/usr/bin/python

import sys
import codecs
import urllib
import urllib2
import json
from multiprocessing import Pool

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


def read_file(filename, maxlines):
    data = []
    if filename:
        data = codecs.open(filename,'r','utf-8').readlines()
    data = [s.decode('utf-8') for s in sys.stdin]

    nlines = len(data)
    if maxlines:
        nlines = min(maxlines, len(data))
    return nlines, data

def write_output(filename, translations):
    if filename:
        if filename == '-':
            for line in translations:
                print line.encode('utf-8')
        else:
            of = open(filename, 'w')
            for line in translations:
                of.write(line.encode('utf-8'))
                of.write('\n')
        return True
    return False


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-source', help='source data, default: read from stdin')
    #parser.add_argument('-target', help='target data for comparision, optional')
    parser.add_argument('-out', help='output file, if \'-\': write to stdout')
    parser.add_argument('-server', help='server address, default: localhost', default="127.0.0.1")
    parser.add_argument('-port', help='server port, default: 8080', type=int, default=8080)
    parser.add_argument('-nthreads', help='number of threads, default: 10', type=int, default=10)
    parser.add_argument('-maxlines', help='max number of lines to test, default: all', type=int)
    parser.add_argument('-slang', action='store', help='source language code', required=True)
    parser.add_argument('-tlang', action='store', help='target language code', required=True)
    parser.add_argument('-verbose', action='store_true', help='verbose mode')
    args = parser.parse_args(sys.argv[1:])

    pool = Pool(processes=args.nthreads)

    url_template = "http://%s:%s" %(args.server, args.port) + \
                   "/translate?q=%s&key=0&"+ \
                   "target=%s&source=%s" %(args.tlang, args.slang)

    maxlines, source_data = read_file(args.source, args.maxlines)
    queries = (wrap_query(url_template, s) for s in source_data[:maxlines])
    queries = list(queries)
    assert len(queries) == maxlines

    if args.verbose:
        sys.stderr.write("loaded %s sentences\n" %(len(source_data)))
        sys.stderr.write("processing %s queries  in %s threads...\n"
                         %(maxlines, args.nthreads))

    # hammertime
    translations = pool.map(query_server, queries)

    if write_output(args.out, translations) and args.verbose:
        sys.stderr.write("wrote %s translations to %s\n" %(len(translations), args.out))
