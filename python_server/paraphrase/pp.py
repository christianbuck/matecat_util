#!/usr/bin/python

import sys
import codecs
import urllib
import urllib2
import json

def get_nbest_from_json(d):
    """ extract translation from a parsed json object
    d = Responses looking like this:
    {
      "data": {
        "translations": [
          {
            "nbest": ["food", "nutrition"]
          }
        ]
      }
    }
    """
    assert 'data' in d
    assert 'translations' in d['data']
    assert len(d['data']['translations']) == 1
    assert 'nbest' in d['data']['translations'][0]
    return [n['translatedText'] for n in d['data']['translations'][0]['nbest']]

def query_server(query, timeout=120):
    try:
        response = urllib2.urlopen(query, timeout=timeout)
    except:
        return 'TIMEOUT'
        sys.stderr.write("timeout for query: %s\n" %query)
    response_data = json.load(response)
    return response_data

def wrap_query(url_template, line):
    line = urllib.quote(line.encode('utf-8').strip())
    url = url_template %line
    return url


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-server', help='server address, default: localhost', default="127.0.0.1")
    parser.add_argument('-serverinv', help='server address, default: localhost', default="127.0.0.1")
    parser.add_argument('-n', help='the n in n-best. default: 10', type=int, default=10)
    parser.add_argument('-port', help='server port, source->pivot, default: 8644', type=int, default=8644)
    parser.add_argument('-portinv', help='server port, pivot->source, default: 8655', type=int, default=8655)
    parser.add_argument('-slang', action='store', help='source language code', required=True)
    parser.add_argument('-plang', action='store', help='pivot language code', required=True)
    parser.add_argument('-verbose', action='store_true', help='verbose mode')
    parser.add_argument('-timeout', type=int, help='timeout for server queries in s, default: 120', default=120)
    args = parser.parse_args(sys.argv[1:])

    #print args
    # how to query to source-to-pivot server
    url_template = "http://%s:%s" %(args.server, args.port) + \
                   "/translate?q=%s&key=0"+ \
                   "&source=%s&target=%s" %(args.slang, args.plang) + \
                   "&nbest=%d" %(args.n)

    # how to query the pivot-to-source server
    url_template_inv = "http://%s:%s" %(args.serverinv, args.portinv) + \
                   "/translate?q=%s&key=0"+ \
                   "&source=%s&target=%s" %(args.plang, args.slang) + \
                   "&nbest=%d" %(args.n)

    for line in sys.stdin:
        line = line.decode("utf-8").split('|')
        assert len(line) == 3, "expected format: left context | words to paraphrase | right context\n"
        query = wrap_query(url_template, line[1])
        #print query
        pivot = query_server(query, timeout=args.timeout)
        nbest_pivot = get_nbest_from_json(pivot)

        paraphrases = []
        for hyp in nbest_pivot:
            print "pivot hyp: ", hyp

            #query = wrap_query(url_template_inv, hyp.decode("utf-8").strip())
            query = wrap_query(url_template_inv, hyp.strip())
            #print query
            data_paraphrases = query_server(query, timeout=args.timeout)
            #print data_paraphrases
            nbest_paraphrases = get_nbest_from_json(data_paraphrases)
            for para_hyp in nbest_paraphrases:
                print "\t", para_hyp
                paraphrases.append(para_hyp)

        # better: keep scores and add them up in a dict
        paraphrases = list(set(paraphrases))

    print "Paraphrases: "
    for p in paraphrases:
        print p
