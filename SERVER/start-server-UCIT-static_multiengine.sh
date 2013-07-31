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
port=8580
serverThreads=2
serververbose=0
src=en
trg=it
MODELS=$matecatdir/data/UCIT_system/MODELS

#parameters for Moses
mosescmd=$mosesdir/bin/moses
moses_config=${MODELS}/moses-static.ini
moses1_config=${MODELS}/moses-static.ini
moses2_config=${MODELS}/moses-static.ini

#System names
system_name="SYSTEM"
system1_name="SYSTEM1"
moses2_name="MOSES2"

#path of the file containing the map from segment ID to engine names
#use an empty string if not available 
segment2system="/path/to/segment/to/system"
#segment2system=""

threads=2

#parameters to handle the MT server
fixedmosesoptions="-v 0 -threads $threads -async-output -print-id"

#parameters to handle passthrough tag
fixedmosesoptions="$fixedmosesoptions -print-passthrough -print-passthrough-in-n-best -report-segmentation"

#parameters to forcetranslate and notranslate  spans
fixedmosesoptions="$fixedmosesoptions -xml-input inclusive"

#basic command
exe="$python $server -ip $ip -port $port -slang $src -tlang $trg -nthreads $serverThreads"

#added parameters for (up to four different) Moses engines
exe="$exe -moses $mosescmd -options \"${fixedmosesoptions} -f $moses_config \" -system-name $system-_name"
if [ $moses1_config != "" ] ; then exe="$exe -moses1 $mosescmd -options1 \"${fixedmosesoptions} -f $moses1_config\" -system1-name $system1_name" ; fi
if [ $moses2_config != "" ] ; then exe="$exe -moses2 $mosescmd -options2 \"${fixedmosesoptions} -f $moses2_config\" -system2-name $system2_name" ; fi
if [ $moses3_config != "" ] ; then exe="$exe -moses3 $mosescmd -options3 \"${fixedmosesoptions} -f $moses3_config\" -system3-name $system3_name" ; fi

if [ $segment2system != "" ] ; then exe="$exe -segment2system=$segment2system"; fi

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

