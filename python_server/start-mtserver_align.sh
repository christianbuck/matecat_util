#!/bin/bash

SCRIPTS=/home/buck/net/build/moses-uli/scripts

server=./server.py

#parameters for the Moses server
mosesserver_ip=129.215.197.10
mosesserver_port=8080
mosesurl="http://${mosesserver_ip}:${mosesserver_port}/RPC2"

#parameters for the web-service
ip=127.0.0.1
port=8081
src=en
tgt=it

#pointers to scripts for pre- and post-processing
tokenizer="$SCRIPTS/tokenizer/tokenizer.perl -b -a"
detokenizer="$SCRIPTS/tokenizer/detokenizer.perl -b"
verbose=1
logprefix=test

# parameters for online MGIZA
MGIZA=/home/buck/net/build/onlineMGIZA/bin/mgiza
S=en
T=it
S2T=/home/buck/net/build/onlineMGIZA/toy-en-it
T2S=/home/buck/net/build/onlineMGIZA/toy-it-en
S2TMODEL=${S2T}/en-it
T2SMODEL=${T2S}/it-en
TMP=`pwd`


#run command
# put "$|=1;" in lowercase.perl to disable buffering
python $server \
        -pretty \
        -verbose $verbose \
        -port $port -ip $ip \
        -slang $src -tlang $tgt \
        -mosesurl $mosesurl \
        -tokenizer "$tokenizer -b -l $src" \
        -detokenizer "$detokenizer -l $tgt" \
        -tgt-tokenizer "$tokenizer -l $tgt" \
        -omgiza_src2tgt "$MGIZA ${S2TMODEL}.gizacfg -onlineMode 1 -coocurrencefile ${S2T}/${S}_${T}.cooc -corpusfile ${S2T}/${S}_${T}.snt -previousa ${S2TMODEL}.a3.final -previousd ${S2TMODEL}.d3.final -previousd4 ${S2TMODEL}.d4.final -previousd42 ${S2TMODEL}.D4.final -previoushmm ${S2TMODEL}.hhmm.5 -previousn ${S2TMODEL}.n3.final -previoust ${S2TMODEL}.t3.final -sourcevocabularyfile ${S2T}/$S.vcb -sourcevocabularyclasses ${S2T}/$S.classes -targetvocabularyfile ${S2T}/$T.vcb -targetvocabularyclasses ${S2T}/$T.classes -o ${TMP} -m1 0 -m2 0 -m3 0 -m4 3 -mh 0 -restart 11" \
        -omgiza_tgt2src "$MGIZA ${T2SMODEL}.gizacfg -onlineMode 1 -coocurrencefile ${T2S}/${T}_${S}.cooc -corpusfile ${T2S}/${T}_${S}.snt -previousa ${T2SMODEL}.a3.final -previousd ${T2SMODEL}.d3.final -previousd4 ${T2SMODEL}.d4.final -previousd42 ${T2SMODEL}.D4.final -previoushmm ${T2SMODEL}.hhmm.5 -previousn ${T2SMODEL}.n3.final -previoust ${T2SMODEL}.t3.final -sourcevocabularyfile ${T2S}/$T.vcb -sourcevocabularyclasses ${T2S}/$T.classes -targetvocabularyfile ${T2S}/$S.vcb -targetvocabularyclasses ${T2S}/$S.classes -o ${TMP} -m1 0 -m2 0 -m3 0 -m4 3 -mh 0 -restart 11" \
        -symal "/home/buck/net/build/tools/symal -alignment=grow -diagonal=yes -final=yes -both=yes"

        #-truecaser "$SCRIPTS/tokenizer/lowercase.perl" \
        #-tgt-truecaser "$SCRIPTS/tokenizer/lowercase.perl" \





    #parser.add_argument('-symal', help="path to symal, including arguments")
    #parser.add_argument('-omgiza_src2tgt', help='path of online-MGiza++, including arguments for src-tgt alignment')
    #parser.add_argument('-omgiza_tgt2src', help='path of online-MGiza++, including arguments for tgt-src alignment')
