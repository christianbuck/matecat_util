#!/bin/bash 

# Uses MGiza to align source and target and saves all the models
# Arguments: source_corpus target_corpus source_language target_language
# Example: $0 en.txt it.txt en it
# This will produce an alignment where target (it) word is aligned to 
# zero or one source (en) words. Every source (en) word may be aligned to
# any number or target (it) words.


DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BIN=$DIR/bin
MGIZA=/path/to/the/regular/mgiza
cp -v $DIR/default.gizacfg .
SOURCE_CORPUS=$1
TARGET_CORPUS=$2
S=$3
T=$4

ln -sv $SOURCE_CORPUS $S
ln -sv $TARGET_CORPUS $T
mkdir -p $3-$4

echo "1. MKCLS"
#$BIN/mkcls -n10 -p$S -V$S.classes &
#$BIN/mkcls -n10 -p$T -V$T.classes &
echo $BIN/mkcls -n10 -p$S -V$S.classes
echo $BIN/mkcls -n10 -p$T -V$T.classes
wait

echo "2. PLAIN2SNT"
#$BIN/plain2snt $S $T

echo "3. SNT2COOC"
echo $BIN/snt2cooc ${S}_${T}.cooc ${S}.vcb ${T}.vcb ${S}_${T}.snt
#$BIN/snt2cooc ${S}_${T}.cooc ${S}.vcb ${T}.vcb ${S}_${T}.snt

INLINEARGS="-coocurrencefile ${S}_${T}.cooc -corpusfile ${S}_${T}.snt -targetvocabularyclasses ${T}.classes -targetvocabularyfile ${T}.vcb -sourcevocabularyclasses ${S}.classes -sourcevocabularyfile ${S}.vcb -ncpus 8"

echo "4. RUNNING MGIZA ... this may take a while"
echo $MGIZA default.gizacfg $INLINEARGS -o $S-$T
$MGIZA default.gizacfg $INLINEARGS -o $S-$T

echo "DONE!"

