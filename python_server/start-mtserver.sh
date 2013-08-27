#!/bin/bash

SCRIPTS=${MTSERVER_ROOT}

server=${MTSERVER_ROOT}/python_server/server.py

#parameters for the Moses server
mosesserver_ip=127.0.0.1
mosesserver_port=${MOSES_PORT}
mosesurl="http://${mosesserver_ip}:${mosesserver_port}/RPC2"

#parameters for the web-service
ip=${MTSERVER_URL}
port=${MTSERVER_PORT}
src=${MTSERVER_SRCLNG}
tgt=${MTSERVER_TGTLNG}

#pointers to scripts for pre- and post-processing
tokenizer="$SCRIPTS/tokenizer/tokenizer.perl -b -X -l $src -a"
detokenizer="$SCRIPTS/tokenizer/detokenizer.perl -b -l $tgt"
verbose=1
logprefix=test

#run command
python $server \
	-pretty \
	-verbose $verbose \
	-port $port -ip $ip \
	-slang $src -tlang $tgt \
	-mosesurl $mosesurl \
	-tokenizer "$tokenizer" \
	-detokenizer "$detokenizer"

