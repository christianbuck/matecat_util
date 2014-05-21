#!/usr/bin/perl -w

use strict;
use utf8;
use Switch;

BEGIN {
  my $date=`date`;
  print STDERR "Alignment script is starting.\t$date";

  die "ERROR: wrong number of argument ($#ARGV instead of 2)\n
  Usage: $0 src2tgt.gz tgt2ref.gz > src2ref (STDOUT)\n\n" if ($#ARGV != 1); # $#ARGV=1 <=> 2 arguments
}

END {
  my $date=`date`;
  print STDERR "End of alignment script.\t$date";
}

#########################################################################################################################
## Synopsys: align bitext (SRC & REF) using translation of source side as pivot
## Requirements: 1/ Moses word-to-word alignment between SRC & TGT      [src2tgt]
##               2/ Tercpp alignment computed between TGT & REF         [tgt2ref]
## Output: SRC<=>REF alignments (format: 0-0 1-1 2-2 3-.. )             [src2ref]
#
## Usage: perl bitext-tokalign.pl src2tgt.gz tgt2ref.gz > src2ref (STDOUT)
#
## Author - question/support: Fred Blain
#########################################################################################################################

open my $srcfile, "cat $ARGV[0] |" or die "Error: cannot open $ARGV[0]\n";
open my $reffile, "cat $ARGV[1] | egrep '^ALIG:' |" or die "Error: cannot open $ARGV[1]\n";

my $line = 0;
while (my $src2tgt = <$srcfile>)
{
  #print "\n".++$line."---\n"; #DEBUG
  chomp $src2tgt;
  print STDERR "\nsrc2tgt:|".$src2tgt."|\n"; #DEBUG
  my $tgt2ref = <$reffile>; chomp $tgt2ref;
  print STDERR "\ntgt2ref:|".$tgt2ref."|\n"; #DEBUG

  # ####################################
  # ###### SRC <=> TGT alignments
  # ####################################
  my %hashSRC2TGT = ();
  foreach my $vc (split(' ',$src2tgt))
  {
    my ($src,$tgt) = ($vc =~ m/(\d+)-(\d+)/);
    $hashSRC2TGT{$src}{$tgt} = 1;
  } #foreach

  # ####################################
  # ###### TGT <=> REF alignments
  # ####################################
  my (%hashTGT2REF, %hashTemp, @tabTGT) = ();
  #my ($itgt,$iref) = 0;
  my $iref = 0;
  my $itgt = 0;
  my ($alignments,$nbShift,$shifts) = ($tgt2ref =~ /^ALIG:\s(.*)\s+\|\|\|\s+NbrShifts:\s(\d+)\s?(.*)$/);
  my @tabalign = split(' ',$alignments);
  for (my $i=0; $i <= $#tabalign; $i++){ $tabTGT[$i] = $i; }
  foreach my $edType (@tabalign)
  { # either 'A' or 'S', this is an alignment
    switch ($edType)
    {
      case /A|S/ { $hashTemp{$itgt}{$iref}=1; $itgt++; $iref++;}
      case 'I'   { $hashTemp{$itgt}{$iref}=1; $itgt++;}
      case 'D'   { $iref++; }
      else { print "[Error TERCpp alignment] error in editType: $edType\n"; }
    }
  } #foreach edType
  if ($nbShift)
  {
    my @tabShift = ($shifts =~/(\[\d.*?[^\]]+?\])/g);
    for (my $i=$#tabShift; $i>=0; $i--)
    {
      my ($start,$end,$pos) = ($tabShift[$i] =~ /\[(\d+),\s(\d+),\s-?\d+\/(-?\d+)\]/);
      my $size = 1+($end-$start);
      my @shift = ();
      if ($pos > $start)
      {
        @shift = splice(@tabTGT,$pos-$size+1, $size);
        splice(@tabTGT, $start, 0, @shift);
      }
      else
      {
        @shift = splice(@tabTGT,$pos-$size+1, $size);
        splice(@tabTGT, $start-$size, 0, @shift);
      }
    } #for
    for (my $i=0; $i<=$#tabTGT; $i++)
    {
      $hashTGT2REF{$i} = $hashTemp{$tabTGT[$i]} if (exists $hashTemp{$tabTGT[$i]});
    }
  } #if nbshift
  else { %hashTGT2REF = %hashTemp; }


#  ## --- #DEBUG
#  print "src2tgt: ";
#  #foreach my $key (keys %hashSRC2TGT) { print $hashSRC2TGT{$key}."-".$key." "; }
#  foreach my $key (sort keys %hashSRC2TGT) {
#    foreach my $subkey (sort keys %{$hashSRC2TGT{$key}}){ print $key."-".$subkey." "; }
#  }
#  print "\n";
#  print "tgt2ref: ";
#  foreach my $key (sort keys %hashTGT2REF) {
#    foreach my $subkey (sort keys %{$hashTGT2REF{$key}}){ print $key."-".$subkey." "; }
#  }
#  print "\n";
#  ## --- #DEBUG

  # ####################################
  # ###### SRC <=> REF alignments using TGT as pivot
  # ####################################
  my @out = ();
  foreach my $src (sort keys %hashSRC2TGT) {
    foreach my $tgt (sort keys %{$hashSRC2TGT{$src}}) {
      foreach my $ref (sort keys %{$hashTGT2REF{$tgt}}) { $out[++$#out] = $src."-".$ref; }
    }
  }
  print "@out\n";
#  print "src2ref: @out\n";
#  print "\n------------------\n";
} #while

close $srcfile;
close $reffile;
