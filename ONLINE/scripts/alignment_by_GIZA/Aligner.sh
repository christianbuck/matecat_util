#!/usr/bin/env bash

export TMP=/tmp

lngSrc_default="en"
lngTrg_default="it"

experimentName="MSC$$"
tmpdir="$TMP/PhraseExtraction$$/"
outputPrefix="${tmpdir}/${experimentName}"

create_tmpdir=0
if [ ! -d $tmpdir ] ; then
create_tmpdir=1
mkdir -p $tmpdir
fi

function computeBidirectionalAlignment(){
	lngSrc=$1; shift
	lngTrg=$1; shift
	tstSrc=$1; shift
	tstTrg=$1; shift
	src2trg_gizacfg=$1; shift
	trg2src_gizacfg=$1; shift
	sym_type=$1; shift
	model_iteration=$1; shift

	intersect=`echo $sym_type | awk '/intersect/ {print "yes"}'`
	union=`echo $sym_type | awk '/union/ {print "yes"}'`
	grow=`echo $sym_type | awk '/grow/ {print "yes"}'`
	diag=`echo $sym_type | awk '/diag/ {print "yes"}'`
	final=`echo $sym_type | awk '/final/ {print "yes"}'`
	both=`echo $sym_type | awk '/and/ {print "yes"}'`
	if [ $intersect ] ; then align_type="intersect" ; fi
	if [ $union ] ; then align_type="union" ; fi
	if [ $grow ] ; then align_type="grow" ; fi
	if [ ! $diag ] ; then diag="no" ; fi
	if [ ! $final ] ; then final="no" ; fi
	if [ ! $both ] ; then both="no" ; fi

	echo "align_type:$align_type diag:$diag final:$final both:$both"
	echo "model_iteration:$model_iteration"

	m1=`echo $model_iteration | sed -n "s/.*m1=\([0-9]*\).*/\1/p"`; [[ ! $m1 > 0 ]] && m1=0
        m2=`echo $model_iteration | sed -n "s/.*m2=\([0-9]*\).*/\1/p"`; [[ ! $m2 > 0 ]] && m2=0
        m3=`echo $model_iteration | sed -n "s/.*m3=\([0-9]*\).*/\1/p"`; [[ ! $m3 > 0 ]] && m3=0
        m4=`echo $model_iteration | sed -n "s/.*m4=\([0-9]*\).*/\1/p"`; [[ ! $m4 > 0 ]] && m4=0
        mh=`echo $model_iteration | sed -n "s/.*mh=\([0-9]*\).*/\1/p"`; [[ ! $mh > 0 ]] && mh=0
	m5=0
	m6=0
	if [ $m1 -gt 0 ] ; then restart_level=1
	elif [ $m2 -gt 0 ] ; then restart_level=3 ; 
	elif [ $mh -gt 0 ] ; then restart_level=6 ; 
	elif [ $m3 -gt 0 ] ; then restart_level=9 ; 
        elif [ $m4 -gt 0 ] ; then restart_level=11 ;
        else echo "You have to specify at least one iteration of any of one following models: m1, m2, m3, m4, mh"; exit;
        fi 
				

        dump="-onlyaldumps 1 -nodumps 1"
        if [ $m4 -gt 0 ]; then final_step=4; extension="A3.final.part0"; dump="$dump -nofiledumpsyn 1"   # The order is: model 4, 3, hmm, 2, 1
        elif [ $m3 -gt 0 ]; then final_step=3; extension="A3.final.part0"; dump="$dump -nofiledumpsyn 1"
        elif [ $mh -gt 0 ]; then final_step='h'; extension="Ahmm.$mh.part0"; dump="$dump -nofiledumpsyn 0 -hmmdumpfrequency $mh -model1dumpfrequency 0 -model2dumpfrequency 0"
        elif [ $m2 -gt 0 ]; then final_step=2; extension="A2.$m2.part0"; dump="$dump -nofiledumpsyn 0 -model2dumpfrequency $m2 -model1dumpfrequency 0"
        elif [ $m1 -gt 0 ]; then final_step=1; extension="A1.$m1.part0"; dump="$dump -nofiledumpsyn 0 -model1dumpfrequency $m1"
        else echo "You have to specify at least one iteration of any of one following models: m1, m2, m3, m4, mh"; exit;
        fi

	echo "M1=$m1 M2=$m2 M3=$m3 M4=$m4 MH=$mh"
        echo "Restart Level=$restart_level"  
        echo "Final_Step:$final_step"  
	echo "Dump parameters: $dump"
	echo "Giza output extension:$extension"
	echo "Getting srcVcb from $trg2src_gizacfg and trgVcb from $trg2src_gizacfg"
	
	local srcVCB=$(grep "^sourcevocabularyfile" $trg2src_gizacfg | sed -e "s/^sourcevocabularyfile[ \r\t]*//g")
	local trgVCB=$(grep "^targetvocabularyfile" $trg2src_gizacfg | sed -e "s/^targetvocabularyfile[ \r\t]*//g")
	dn=`dirname $srcVCB`
	echo "Updating .VCB and .SNT files"
	
	( echo "1 UNK 0"  ; cat $srcVCB ) > $outputPrefix.src.vcb.tmp
	( echo "1 UNK 0"  ; cat $trgVCB ) > $outputPrefix.trg.vcb.tmp

#	sed "1 i 1 UNK 0"  $srcVCB >  ${outputPrefix}.src.vcb.tmp
#	#echo "SCR VCB is created"
#       sed "1 i 1 UNK 0"  $trgVCB >  ${outputPrefix}.trg.vcb.tmp

	python ${MGIZA}/scripts/plain2snt-hasvcb.py $outputPrefix.src.vcb.tmp $outputPrefix.trg.vcb.tmp  ${tstSrc} ${tstTrg} $outputPrefix.trg-src.snt $outputPrefix.src-trg.snt $outputPrefix.src.vcb $outputPrefix.trg.vcb

	ln -s $dn/vcb.${lngSrc}.classes $outputPrefix.src.vcb.classes
	ln -s $dn/vcb.${lngTrg}.classes $outputPrefix.trg.vcb.classes


	echo "Updating .COOC files"
	${MGIZA}/bin/snt2cooc $outputPrefix.trg-src.cooc $outputPrefix.src.vcb $outputPrefix.trg.vcb $outputPrefix.trg-src.snt
	${MGIZA}/bin/snt2cooc $outputPrefix.src-trg.cooc $outputPrefix.trg.vcb $outputPrefix.src.vcb $outputPrefix.src-trg.snt


	mgiza_parameters=""
	mgiza_parameters="$mgiza_parameters $dump"
	mgiza_parameters="$mgiza_parameters -ncpus 1"
	mgiza_parameters="$mgiza_parameters -m1 $m1 -m2 $m2 -m3 $m3 -m4 $m4 -m5 $m5 -mh $mh"
	mgiza_parameters="$mgiza_parameters -restart $restart_level" 

	mgiza_parameters_dir="${src2trg_gizacfg} $mgiza_parameters \	
        -coocurrence $outputPrefix.src-trg.cooc -c $outputPrefix.src-trg.snt \
        -s $outputPrefix.trg.vcb  -t $outputPrefix.src.vcb \
        -o $outputPrefix.src-trg"
        mgiza_parameters_inv="${trg2src_gizacfg} $mgiza_parameters \
        -coocurrence $outputPrefix.trg-src.cooc -c $outputPrefix.trg-src.snt \
        -s $outputPrefix.src.vcb -t $outputPrefix.trg.vcb \
        -o $outputPrefix.trg-src"
 
	echo "Running force alignment (Forward)"
	echo "Running this command (Forward)"
	echo "${MGIZA}/bin/mgiza $mgiza_parameters_dir"
	${MGIZA}/bin/mgiza $mgiza_parameters_dir

	echo "Running force alignment (Backward)"
	echo "Running this command (Backward)"
	echo "${MGIZA}/bin/mgiza $mgiza_parameters_inv"
	${MGIZA}/bin/mgiza $mgiza_parameters_inv

        if [[ ! -e $outputPrefix.trg-src.$extension || ! -e $outputPrefix.src-trg.$extension ]] ; then
		echo "dummy bilingual alignment"
		(cat ${outputPrefix}.lower.src ${outputPrefix}.lower.trg | perl -pe 's/\n/ \{\#\#\} /' ; echo )> ${outputPrefix}.aligned.${sym_type}
	else
		echo "real bilingual alignment"
		perl ${MGIZA}/scripts/giza2bal.pl -d "$outputPrefix.trg-src.$extension" -i "$outputPrefix.src-trg.$extension" > ${outputPrefix}.giza2bal
		symal_parameters="-alignment=${align_type} -diagonal=$diag -final=$final -both=$both"
		cat ${outputPrefix}.giza2bal | ${MGIZA}/bin/symal $symal_parameters -o="${outputPrefix}.aligned.${sym_type}"
	fi

}


mgiza_dir=""
srcL=""
trgL=""
while [ "1" -eq "1" ] ; do
  case "$1" in
    --src )
      srcFile="$2"; shift 2 ;;
    --trg )
      trgFile="$2"; shift 2 ;;
    --gizacfg-src2trg )
      gizacfg_src2trgFile="$2"; shift 2 ;;
    --gizacfg-trg2src )
      gizacfg_trg2srcFile="$2"; shift 2 ;;
    --sym-type )
      sym_type="$2"; shift 2 ;;
    --models-iterations )
      model_iteration="$2"; shift 2 ;;
    --mgiza )
      mgiza_dir="$2"; shift 2 ;;
    --source_language )
      srcL="$2"; shift 2 ;;
    --target_language )
      trgL="$2"; shift 2 ;;
    -- ) shift; break ;;
    * )
      break ;;
  esac
done

if [ $mgiza_dir ] ; then MGIZA=$mgiza_dir
else
echo "pointer to the MGIZA executable is not set; please, use parameter --mgiza\n"
exit 1
fi

if [ $srcL ] ; then lngSrc=$srcL
else lngSrc=$lngSrc_default
fi

if [ $trgL ] ; then lngTrg=$trgL
else lngTrg=$lngTrg_default
fi

if [ ! -d ${tmpdir} ] ; then mkdir ${tmpdir} ; fi

cat $srcFile | tr '[:upper:]' '[:lower:]' > ${outputPrefix}.lower.src
cat $trgFile | tr '[:upper:]' '[:lower:]' > ${outputPrefix}.lower.trg

computeBidirectionalAlignment ${lngSrc} ${lngTrg} ${outputPrefix}.lower.src ${outputPrefix}.lower.trg ${gizacfg_src2trgFile} ${gizacfg_trg2srcFile} ${sym_type} ${model_iteration} >& ${outputPrefix}.err

cat ${outputPrefix}.aligned.${sym_type} | perl -pe 's/.+\{\#\#\}[ \t]*//'

rm ${outputPrefix}*
if [ $create_tmpdir == "1" ] ; then rm -rf $tmpdir ; fi

exit


