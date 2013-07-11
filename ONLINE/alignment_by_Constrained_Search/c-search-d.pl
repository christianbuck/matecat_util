#!/usr/bin/perl 

# Constrained-Search Algorithm
# DP-based MT search algorithm to find optimal
# match between translation options and one target string
# Copyright Marcello Federico, FBK-irst, 2008

use strict;
use Getopt::Long "GetOptions";


my ($help,$trs,$txt,$debug,$hthresh,$bthresh,$nwp,$dw,$srctgtRatio)=();

################## Default ###################
$hthresh=500;    #histogram threshold
$bthresh=0.8;    #beam threshold
$nwp=-1;         #null word penalty
$dw=0.1;         #distortion weight
$srctgtRatio=1.0;# len(inTgt)/len(inSrc)

$help=1 unless
&GetOptions('trans=s' => \$trs,
            'txt=s' => \$txt,
            'beam-thresh|bt=f' => \$bthresh,
            'ht=i' => \$hthresh,
            'nwp=f' => \$nwp,
            'dw=f' => \$dw,
	    'srctgtR=f' => \$srctgtRatio,
            'debug' => \$debug,
            'help' => \$help,);

if ($help || !$txt || !$trs){
  print "c-search.pl <options>\n",
  "--trans  <string> file with translation options \n",
  "--txt <string>    file with text to be translated\n",
  "--bt [0,1]        beam-search threshold (default 0.8)\n",
  "--ht [0..N]       histogram pruning threshold (default 500)\n",
  "--dw <real>       distortion weight (default 0.1)\n",
  "--nwp <real>      null word penalty (default -1)\n",
  "--srctgtR <real>  tgt to src ratio (default 1.0)\n",
  "--debug           print long output\n",
  "--help            print these instructions\n";    
  exit(1);
}


######### Global variables #################################
my $srclen;
my %SPANS;
my ($E,@E);
#####################################################
select(STDOUT); $|=1;

#read translation options from file "trs"

sub loadoptions{
  my ($from,$to,$src,$span,$phr,$sco)=();
  $srclen=0;
  open(TRANS,"< $trs");
  while (<TRANS>) {
    next if !/\|\|\|/;
    #read: source, span, target, transl. scores
    ($src,$span,$phr,$sco)=split(/\|\|\|/,$_);
    $phr=~s/(^\s+|\s+$)//g;
    $span=~s/(^\s+|\s+$)//g;
    ($from,$to)=split(/-/,$span);
    push @{ $SPANS{"$phr"} },$from,$to;
    #compute source length
    $srclen=($srclen<$to?$to:$srclen);
  }
  $srclen++; 
  print "Max src pos $srclen\n" if $debug;

  if ($debug){
      my ($s,$i);
      for $s ( keys %SPANS ){
	  printf "%s: ", $s;
	  for ($i=0; $i<= $#{$SPANS{$s}}; $i++) {
	      printf "<%s> ", ${$SPANS{$s}}[$i];
	  }
	  printf "\n";
      }
  }
}
 
#add span to coverege set if positions are vacant
sub update{
 
  my($from,$to,$state,$last)=@_;
  my($p,$set)=0;

  print "before:", &state2string($state)," [$from,$to]\n" if $debug;
  return $state if $from==-1;
  
  for ($p=$from;$p<=$to;$p++){
    return -1 if vec($state,$p,1)==1;
    vec($state,$p,1) = 1;
  }
  
  
  ($set,$$last)=unpack("b${srclen}i",$state);
  $state=pack("b${srclen}i",$set,$to);
  print "after:", &state2string($state)," [$from,$to]\n" if $debug;  

  return $state;
}

#print coverage set
sub state2string{
  my ($state)=$_[0];
  return join(" ",unpack("b${srclen}i",$state));
}

# Decoding algorithm
#  Q(i,C) = optimal translation of first i target words, with
#           subset C of source positions/words
#
#  Q(i,C)=   max   Q(i',C') + score(C,C',i,i')
#         i'<i, C'c C, 
#
# 
# for (i2=0;i2<l;i2++)
#   for(i1=-1;i1<=i2;i1++)
#     while (j1,j2)=getspans(E[i1..i2]);
#        lscore=(j2==NULL?0:(j2-j1+1)+(i2-i1));
#        if (i1==-1) // initial case
#            Q(i2,(j1..j2))=lscore
#        else
#           forall C' in Q(i1,C')
#               if !((j1..j2) AND C')
#                   score=Q(i1,C') + lscore;
#                   C=C' OR (j1..j2)
#                   if !Q(i2,C) OR Q(i2,C)<score
#                       Q(i2,C)=score
#                      


sub search{

my @Q; #DP scoring function
my %B; #backtracking structure
my @S; #translation spans

my $count=0;
my @histo=();
my $best;
my $worst;

my ($i1,$i2,$j1,$j2,$s1,$s2,$l1,$l2,$score,$lscore,$phr);


for ($i2=0;$i2<=$#E;$i2++){
  

  $count=0;
  $best=-1000;
  $worst=+1000;

  for ($i1=-1;$i1<$i2;$i1++){

    $phr=join(" ",@E[$i1+1..$i2]);    
    if (defined($SPANS{"$phr"})){
      @S=@{ $SPANS{"$phr"} };
      while (@S){

	($j1,$j2)=splice(@S,0,2);
	printf "[j1,j2] = [$j1,$j2] (tgt[%d,$i2]=$phr)\n",$i1+1  if $debug;
	if ($i1==-1){
	  $s1=pack("b${srclen}i",0,0);
	  $s2=&update($j1,$j2,$s1,\$l1);
	  $score=($j2==-1?$nwp:$srctgtRatio*($j2-$j1+1)+($i2-$i1) - $dw * $j1);
	  $Q[$i2]{"$s2"}=$score;
	  $B{"$i2,$s2"} = [ ($i1,$s1,$j1,$j2) ];
	  printf "Ba{i2=%d,s2=%s} <- [i1=%d,s1=%s,j1=%d,j2=%d]\n\n", $i2,&state2string($s2),$i1,&state2string($s1),$j1,$j2 if $debug;
	  $best=$score if $score > $best;
	  $worst=$score if $score < $worst;
	}else{
	  for $s1 ( keys %{ $Q[$i1] } ){
	    printf "s1 = %s\n", &state2string($s1) if $debug;
	    print "before $l1 \n" if $debug;
	    if (-1!=($s2=&update($j1,$j2,$s1,\$l1))){
	      print "after $l1 \n" if $debug;
	      $score=$Q[$i1]{"$s1"} + 
		($j2==-1 ? $nwp : $srctgtRatio*($j2-$j1+1)+($i2-$i1) - $dw * abs($l1-$j1));
	      #---------------------------------------------------------------
	      # Recombination: 
	      if (!exists($Q[$i2]{"$s2"}) || $score > $Q[$i2]{"$s2"}){
		if ($debug) {
		    if (!exists($Q[$i2]{"$s2"})) {
			printf "Bnew(%f){i2=%d,s2=%s} <- [i1=%d,s1=%s,j1=%d,j2=%d]\n\n", $score, $i2,&state2string($s2),$i1, &state2string($s1),$j1,$j2;
		    } else {
			printf "Bupdate(%f->%f){i2=%d,s2=%s} <- [i1=%d,s1=%s,j1=%d,j2=%d]\n\n", $Q[$i2]{"$s2"}, $score, $i2,&state2string($s2),$i1, &state2string($s1),$j1,$j2;
		    }
		}

		$Q[$i2]{"$s2"}=$score;
		$B{"$i2,$s2"} = [ ($i1,$s1,$j1,$j2) ];
		$best=$score if $score > $best;
		$worst=$score if $score < $worst;
	    } else {
		printf "No Recombination\n\n", if $debug;
	    }
	      #-------------------------------------------------------------- 
	    }
	  }
	}
      }    
    }
  }
  #histogram pruning
  print "best: $best worst: $worst\n" if $debug;
  @histo=();
  my $total;
  for $s2 ( keys %{ $Q[$i2] } ){
    $histo[int(($Q[$i2]{"$s2"} - $worst)/($best-$worst+1) * 500)]++;
    $total++;
  }
  
  my $hpruned=0;
  for ($score=$#histo;$score>=0; $score--){
    $count+=$histo[$score];
    last if $count > $hthresh;
  }
  $score--; # per eliminare hyp dal primo bin successivo quello che ha causato lo sforamento di thresh                  

  if ($score>=0) { # pruning a meno che il bin che causa lo sforamento non sia lo 0                                     
      for $s2 ( keys %{ $Q[$i2] } ){
	  if (int(($Q[$i2]{"$s2"} - $worst)/($best-$worst+1) * 500) <= $score){
	      $hpruned++;
	      delete $Q[$i2]{"$s2"};
	      die "problem\n" if !exists $B{"$i2,$s2"};
	      delete $B{"$i2,$s2"};
	  }
      }
  }

  my $bpruned=0;
  #beam threshold pruning
  if ($i2>=5 and $best>0){
    for $s2 ( keys %{ $Q[$i2] } ){
      if (($Q[$i2]{"$s2"}/$best) < $bthresh){
	$bpruned++;
	delete $Q[$i2]{"$s2"};
	delete $B{"$i2,$s2"};
      }
    }
  }
  print "total: $total hpruned: $hpruned bpruned: $bpruned\n" if $debug;
}


#find best complete solution
$score=-1000; my $out; 
for $s1 ( keys %{ $Q[$#E] } ){
  if ($Q[$#E]{"$s1"}>$score){
    $score=$Q[$#E]{"$s1"};
    $s2=$s1;
  }
}

print "best score ",$score," ",$#E+1," ",$srclen,"\n" if $debug;

#backtrack solution
($i2,$out)=($#E,"");
print &state2string($s2)," ",int(($score-($#E+1))/($srclen) * 100) ," : ";

while ($i2>=0){
  ($i1,$s2,$j1,$j2)=@{ $B{"$i2,$s2"} };
  $out= join(" ",@E[$i1+1..$i2]).($j1<$j2?" [$j1-$j2] ":" [$j1] ").$out;
  print "bt: ",&state2string($s2),"\n" if $debug;
  $i2=$i1;
}
print "$out\n";
return 1;
}

#MAIN CODE

&loadoptions;
my %localdict;

open(TXT,"< $txt ");
while ($E=<TXT>){
  chop $E;
  $E=~s/(^\s+|\s+$)//g;
  @E=split(/ +/,$E);
  my $w;

  #add translation options to NULL word (position -1)
  foreach $w (@E){
    if (!defined($localdict{$w})){
      $localdict{$w}=1;
      push @{ $SPANS{"$w"} },-1,-1;
    }
  }

  &search;

}


