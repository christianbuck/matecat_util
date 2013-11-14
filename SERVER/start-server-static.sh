#!/bin/bash

logprfx=$1; shift;

source /path/to/configuration/file
# ex: 
# source MATECAT/.bashrc.MATECAT

matecatdir=/path/to/main/MATECAT/dir
# ex:
# matecatdir=/home/bertoldi/MATECAT
softwaredir=$matecatdir/code/software
python=/path/to/python-2.7.2

server=$softwaredir/SERVER/server_static.py

mosesdir=/path/to/moses/dir
# ex:
# mosesdir=$softwaredir/MOSES/
# note that moses executable is expected in $mosesdir/bin/moses

#parameters for the web-service
ip=127.0.0.1
port=8480
serverThreads=2
serververbose=0
src=en
trg=it
MODELS=$matecatdir/data/UCIT_system/MODELS

#parameters for Moses
mosescmd=$mosesdir/bin/moses
mosesconfig=${MODELS}/moses-static.ini

threads=2

#basic Moss parameter
mosesoptions="-f $mosesconfig -v 0 -threads $threads -async-output -print-id"

#parameters to handle passthrough tag
mosesoptions="$mosesoptions -print-passthrough -print-passthrough-in-n-best -report-segmentation"

#parameters to forcetranslate and notranslate  spans
mosesoptions="$mosesoptions -xml-input inclusive"

exe="$python $server -ip $ip -port $port -moses $mosescmd -options \"${mosesoptions}\" -slang $src -tlang $trg -nthreads $serverThreads"

#parameters for Logging
if [ $logprfx != "" ] ; then exe="$exe -logprefix=$logprfx"; fi


#parameters for server
#exe="$exe -verbose $serververbose -persist"
exe="$exe -persist"


#parameters for Preprocessing
exe="$exe -prepro "

preprocesscmd="$softwaredir/code/tokenizer/tokenizer.perl -X -b -l $src"
exe="$exe \"$preprocesscmd\""

preprocesscmd="$softwaredir/code/monolingual/accents.pl -b -l $src"
exe="$exe \"$preprocesscmd\""

preprocesscmd="$python -u $softwaredir/code/tags4moses/annotate_words.py"
exe="$exe \"$preprocesscmd\""

preprocesscmd="$softwaredir/code/tags4moses/reinsert_forcetranslate.pl -b -moses"
exe="$exe \"$preprocesscmd\""


#parameters for Postprocessing

hmm_dir=${MODELS}/alignment/
hhmm=${hmm_dir}/en-it.hhmm.5
thmm=${hmm_dir}/en-it.thmm.5
srcvcb=${hmm_dir}/en-it.trn.src.vcb
trgvcb=${hmm_dir}/en-it.trn.trg.vcb

lex_dir=${MODELS}/
srclex=${lex_dir}/lex.en-it
trglex=${lex_dir}/lex.it-en


exe="$exe -postpro "

##postprocesscmd="$python $softwaredir/code/tags4moses/hmmalign.py  $hhmm $thmm $srcvcb $trgvcb"
##postprocesscmd="$python $softwaredir/code/tags4moses/dummyalign.py $srcvcb $trgvcb"
ibm1align_options="-printXmlWordAlignment -printXmlPhraseAlignment"
postprocesscmd="$python $softwaredir/code/tags4moses/ibm1align.py $srclex $trglex $ibm1align_options"
exe="$exe \"$postprocesscmd\""

postprocesscmd="$softwaredir/code/tags4moses/deannotate_words.pl -b -collapse -p"
exe="$exe \"$postprocesscmd\""

postprocesscmd="$softwaredir/code/tokenizer/detokenizer.perl -b -l $trg"
exe="$exe \"$postprocesscmd\""

echo $exe

eval "${exe} &"
echo "SERVER PID:$!"

