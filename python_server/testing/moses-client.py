#!/usr/bin/env python
# -*- coding: utf-8 -*-

# python port of client.perl

import os
import xmlrpclib
import datetime

#parameters for the Moses server
mosesserver_ip = "127.0.0.1"
mosesserver_ip = os.environ.get('MOSES_URL')
mosesserver_port = os.environ.get('MOSES_PORT')

url = "http://" + mosesserver_ip + ":" + mosesserver_port + "/RPC2"
proxy = xmlrpclib.ServerProxy(url)

text = u"European Parliament"

alignflag = False
reportflag = False
params = {"text":text, "align":alignflag, "report-all-factors":reportflag}

result = proxy.translate(params)
print result['text']
if alignflag is True:
    if 'align' in result:
        print "Phrase alignments:"
        aligns = result['align']
        for align in aligns:
            print "%s,%s,%s" %(align['tgt-start'], align['src-start'], align['src-end'])

