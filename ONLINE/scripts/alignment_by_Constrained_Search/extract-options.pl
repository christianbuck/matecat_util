#! /usr/bin/perl

use strict;

$|=1;

my $inflag=0;
my (@words) =();

# read translation options from section "Translation Option Collection"
# output the future cost and all feature scores (in this order)

my $defaultscore = -100;
my $defaultscorestring = "";
my $numberoffeatures = 0;
while (my $line=<STDIN>){
	chomp($line);

	$line =~ s/\t+//g;
	
	if ($line =~ /The global weight vector.*?:/){
#		$line =~ s/The global weight vector.*?:\s*//; DEC2010
#		$numberoffeatures=split(/[ \t]+/,$line); #DEC2010

		$line =~ s/The global weight vector.*?:\s*core=\((.*)\)/$1/; #DEC2013
		$numberoffeatures=split(/[,]+/,$line); #DEC2013
		$defaultscorestring = " $defaultscore";
		for (my $i=0; $i<$numberoffeatures; $i++){
			$defaultscorestring .= " $defaultscore";
		}
		next;

	}

	if ($line =~ /TRANSLATING|^Translating:/){
		@words = ();
		print STDOUT "$line\n";
#		$line =~ s/.*TRANSLATING\([0-9]+\):\s+|\s+$//g; # 2009 DECODER 
#		$line =~ s/Translating:\s+|\s+$//g; # 2010 DECODER 
		$line =~ s/Translating:\s+|\s+$//g; # 2013 DECODER 
		@words=split(/[ \t]+/,$line);

		#printing verbatim translation of each source words
		for (my $i=0;$i<scalar(@words);$i++){
		    print STDOUT "$words[$i] ||| $i-$i ||| $words[$i] ||| $defaultscorestring\n";
		}
		next;
	}

#	$inflag=0 if $line !~ /\[\[.*\]\]\<\<.*\>\>\s*$/; #DEC2010
	$inflag=0 if $line !~ /\[\[.*\]\]core=.*$/; #DEC2013
#	$inflag=0 if $line =~ /Total translation options:/;
	$inflag=1, next if $line =~ /Translation Option Collection/;
	next if $line =~ /^$/;

	next if $inflag==0;
#	my ($trg,$futurecost,$start,$end,$scores) = ($line =~/^(.+?)\s+\, pC=.*c=(\S+)\s+\[\[(\d+)\.\.(\d+)\]\]*\<\<(.+?)\>\>/); #DEC2009

#	my ($trg,$futurecost,$start,$end,$scores) = ($line =~/^(.+?)\s+[\,\:]+ pC=.*c=(\S+)\s+\[\[(\d+)\.\.(\d+)\]\]*\<\<(.+?)\>\>/); #DEC2010
#	$scores =~ s/\,//g; #DEC2010

#	my ($trg,$futurecost,$start,$end,$scores) = ($line =~/^(.+?)\s+[\,\:]+ .*c=(\S+)\s+\[\[(\d+)\.\.(\d+)\]\]core=\((.+?)\)/); #DEC2013
	my ($trg,$futurecost,$start,$end,$scores) = ($line =~/^(.+?)\s+\:\:\s+c=\S+\s+c=(\S+)\s+\[\[(\d+)\.\.(\d+)\]\]core=\((.+?)\)/); #DEC2013
	$scores =~ s/\,/ /g; #DEC2013

	my $src=join(" ",@words[$start..$end]);
	my $span="$start-$end";

	print STDOUT "$src ||| $span ||| $trg ||| $futurecost $scores\n";
}
