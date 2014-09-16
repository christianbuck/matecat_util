#!/usr/bin/perl -w

#map taken from resilientparser.py

use strict;
use constant     SPACE_UNDEFINED => -1;           # undefined (used for the inner words, but the first, of NONEMPTY tags
use constant     SPACE_NO => 0;                   # ex: the<a>data
use constant     SPACE_ONLY_BEFORE => 1;          # ex: the <a>data
use constant     SPACE_ONLY_AFTER => 2;           # ex: the<a> data
use constant     SPACE_BEFORE_AND_AFTER => 3;     # ex: the <a> data
use constant     SPACE_INTERNAL => 100;           # ex: <a />  (used only for self_contained tag

use constant CONTAINS_NONEMPTY_TEXT => 0;
use constant CONTAINS_EMPTY_TEXT => 1;
use constant SELF_CONTAINED => 2;
use constant OPENED_BUT_UNCLOSED => 3;
use constant CLOSED_BUT_UNOPENED => 4;
use constant NOTRANSLATE => 5;
use constant FORCETRANSLATE => 6;

#use MateCat;
use Getopt::Long;

# parameter variables
my $help = undef;
#my $enc = $MATECAT_ENC;
my $enc = 'UTF8';
my $collapse = 0;
my $escape = 0;
my $bflag = 0;
my $printpassthrough = 0;
my $force_insert_all = 0;
my $avoid_duplicate_insertion = 0;

# parameter definition
GetOptions(
  "help" => \$help,
  "b" => \$bflag,
  "p" => \$printpassthrough,
  "encoding=s" => \$enc,
  "collapse" => \$collapse,
  "escape" => \$escape,
  "force-insert-all" => \$force_insert_all,
  "avoid-duplicate-insertion" => \$avoid_duplicate_insertion,
) or exit(1);

my $required_params = 0; # number of required free parameters
my $optional_params = 5; # maximum number of optional free parameters

# command description
sub Usage(){
	warn "Usage: deannotate_words.pl [options] < input > output\n";
	warn "	-help \tprint this help\n";
	warn "  -b    \tdisable Perl buffering.\n";
	warn "  -p    \tprint passthrough xml tag\n";
	warn "	-encoding=<type> \tinput and output encoding type\n";
	warn "	-collapse \tenable collapsing of adjacent tags\n";
	warn "	-escape   \tescape \n";
        warn "  -force-insert-all\tmake sure no tag is dropped\n";
        warn "  -avoid-duplicate-insertion\tmake sure no tag is inserted twice\n";

}

if (scalar(@ARGV) < $required_params || scalar(@ARGV) > ($required_params+$optional_params) || $help) {
    &Usage();
    exit;
}

if ($bflag){ $| = 1; }

### insert here the code

my $err = 0; # global error counter
my $nr = 0; # line counter

while (my $line=<STDIN>){
        $nr++;
	chomp($line);
	my $passthrough = "";
	my $trans = "";

	while ($line =~ /^<passthrough[^>]*\/>/){
		$line =~ s/(^<passthrough[^>]*\/>)\s*(.*)$/$2/;
		$passthrough .= "$1";
	}
	$trans = "$line";

#parsing translation
	my @trgwords = split (/[ \t]+/, $trans);
	# even entries contain words, odd entries contain word-alignemnt
        my %to_be_covered; # record which source words will be eventually covered
	for (my $i=0; $i < scalar(@trgwords); $i+=2){
		$trgwords[$i+1] =~ s/\|//g; #remove pipeline from word alignemnt
                $to_be_covered{$trgwords[$i+1]} = 1; # this source word will be covered
	}

#parsing passthrough
	my ($tag) = ($passthrough =~ /<passthrough[ \t]+tag=\"(.*?)\".*\/>/);
	my @tags = split(/\|\|/,$tag);
	my %xml = ();
	my %endxml = ();
	my %typexml = ();
	for (my $i=0; $i < scalar(@tags); $i++){
		my ($idx,$value,$type,$spacetype) = ($tags[$i] =~ /(\-?\d+)\#(.*?)\#(\d+)\#(\-?\d+)$/);
	
		$value =~ s/\&lt;(.+?)&gt;/$1/;
		$value =~ /^([^ \t]*)([ \t].+)?$/;
		my $mainvalue = $1;

		my ($start_space_left, $start_space_right, $end_space_left, $end_space_right, $self_space_internal) = ("","","","","");
 		if (!defined($xml{$idx})){
			$xml{$idx} = "";	
			$endxml{$idx} = "";	
			$typexml{$idx} = "";	
		}

		if ($spacetype != SPACE_UNDEFINED){
			my $s = $spacetype;
			if ($spacetype >= SPACE_INTERNAL){
				if ($type == SELF_CONTAINED ){
					$self_space_internal = " ";	
				}
				$spacetype = $spacetype - SPACE_INTERNAL;
			}
			if ($type == CONTAINS_NONEMPTY_TEXT || $type == CONTAINS_EMPTY_TEXT ){
				my $e = $spacetype % 10;
                                if ( $e == SPACE_BEFORE_AND_AFTER ){
                                        $end_space_left = $end_space_right = " ";
                                }elsif ( $e == SPACE_ONLY_BEFORE ){
                                        $end_space_left = " ";
                                }elsif ( $e == SPACE_ONLY_AFTER ){
                                        $end_space_right = " ";
				}			
				$s = int($spacetype / 10);
			}
			
                        if ( $s == SPACE_BEFORE_AND_AFTER ){
                        	$start_space_left = $start_space_right = " ";
                        }elsif ($s == SPACE_ONLY_BEFORE ){
                        	$start_space_left = " ";
                        }elsif ($s == SPACE_ONLY_AFTER ){
                                $start_space_right = " ";
                        }
		}

		if ($type == CONTAINS_NONEMPTY_TEXT  || $type == NOTRANSLATE || $type == FORCETRANSLATE ){
                        $xml{$idx} .= "${start_space_left}<$value>${start_space_right}";
                        $endxml{$idx} = "${end_space_left}</$mainvalue>${end_space_right}$endxml{$idx}";
			$typexml{$idx} = $type;	
                }elsif ($type == CONTAINS_EMPTY_TEXT){
                        $xml{$idx} .= "${start_space_left}<$value>${start_space_right}${end_space_left}</$mainvalue>${end_space_right}";
                        $typexml{$idx} = $type;
                }elsif ($type == SELF_CONTAINED){
                        $endxml{$idx} .= "${start_space_left}<$value${self_space_internal}/>${start_space_right}";
                        $typexml{$idx} = $type;
                }elsif ($type == OPENED_BUT_UNCLOSED){
                        $xml{$idx} .= "${start_space_left}<$value>${start_space_right}";
                        $typexml{$idx} = $type;
                }elsif ($type == CLOSED_BUT_UNOPENED){
                        $xml{$idx} .= "${start_space_left}</$mainvalue>${start_space_right}";
                        $typexml{$idx} = $type;
                }else{
                        die "Third field should have one of the following values: ",join(",",(CONTAINS_NONEMPTY_TEXT,CONTAINS_EMPTY_TEXT,SELF_CONTAINED,OPENED_BUT_UNCLOSED,CLOSED_BUT_UNOPENED,NOTRANSLATE,FORCETRANSLATE)),"\n";
                }
	}

#reconctructing the tagged output
	my $out ="";

	#adding tags not associated to any source word
        for (my $i=0; $i < scalar(@tags); $i++){
		my ($idx,$value,$type,$spacetype) = ($tags[$i] =~ /(\-?\d+)\#(.*?)\#(\d+)\#(\-?\d+)$/);
		if ($idx == -1 && defined($xml{$idx})){
                        $out = $xml{$idx}.$endxml{$idx};
		}
	}

# going through output words and putting tags there from the source
        my %xmlused = (); # record if we have implanted all the tags
        my $used_up_to = -1; # record which source words have already been considered
        for (my $i=0; $i < scalar(@trgwords); $i+=2){
		my $srcidx = $trgwords[$i+1];
                if ($srcidx != -1 && $used_up_to < $srcidx && $force_insert_all) {
                  for (my $j=$used_up_to; $j <= $srcidx; $j++) {
                    next if $j == -1;
                    if (defined $xml{$j} && !$to_be_covered{$j}) {
                      # the source word $j has a tag and is not going to be emitted
                      $xmlused{$j}++;
                      $out .= "$xml{$j}$endxml{$j}";
                    }
                  }
                  $used_up_to = $srcidx;
                }
                my $do_implant = 0;
		if ($srcidx != -1 && defined($xml{$srcidx})){
                        $do_implant = 1;
                        if ($xmlused{$srcidx}) {
                          if ($avoid_duplicate_insertion) {
                            $do_implant = 0;
                          } else {
                            print STDERR "$nr: Warning, implanting a tag that was already implanted: $xml{$srcidx} $endxml{$srcidx}\n"
                          }
                        }
                }
                if ($do_implant) {
                        $xmlused{$srcidx}++;
                        $out .= $xml{$srcidx}.$trgwords[$i].$endxml{$srcidx};
		}else{
			$out .= "$trgwords[$i] ";
		}
	}
        foreach my $srcidx (keys %xml) {
          if ($xmlused{$srcidx} == 0) {
            print STDERR "$nr:Did not reimplant the tags $xml{$srcidx} $endxml{$srcidx}\n";
            $err++;
          } elsif ($xmlused{$srcidx} > 1 && $avoid_duplicate_insertion) {
            print STDERR "$nr:BUG: tags reimplanted more than once: $xml{$srcidx} $endxml{$srcidx}\n";
          }
        }

# collapse tags
	if ($collapse){
		my $contflag=1;
		my $newout = "";
		while ($contflag){
			$contflag=0;
			$newout = "";

			while ($out =~ s/(.*?)(<\/[ ]*([^ >]+?)[ ]*>[ \t]*<(([^ \t>\/]+?)([ \t][^>]*>|>)))//){

				$newout .= " $1 ";
				my $endtag = $3;
				my $starttag = $5;
				if ($endtag eq $starttag){
					$contflag=1;
				}
				else
				{
					$newout .= " $2 ";
				}
			}
			$newout .= " $out ";
			$out = $newout;
		}
	}

# removing index of tags
        $out =~ s/(<\/?)([^> ]+)_\d+/$1$2/g;

# escaping (or not) some characters
	if ($escape){
		$out =~ s/</&lt;/g;
		$out =~ s/>/&gt;/g;
	}
	else{
		$out =~ s/\&amp;/\&/g;
		$out =~ s/\&quot;/\"/g;
	}

# removing double spaces and spaces at the beginning and end of the line
        $out =~ s/[ \t]+/ /g;
        $out =~ s/^[ \t]//g;
        $out =~ s/[ \t]$//g;
        $out =~ s/>[ ]+</></g;
	if ($printpassthrough){ print "$passthrough"; }
	print "$out\n";
}

exit 1 if $err;
