#!/usr/bin/perl -w

#map taken from resilientparser.py

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
my $enc = UTF8;
my $collapse = 0;
my $escape = 0;
my $bflag = 0;
my $printpassthrough = 0;

# parameter definition
GetOptions(
  "help" => \$help,
  "b" => \$bflag,
  "p" => \$printpassthrough,
  "encoding=s" => \$enc,
  "collapse" => \$collapse,
  "escape" => \$escape,
) or exit(1);

my $required_params = 0; # number of required free parameters
my $optional_params = 5; # maximum number of optional free parameters

# command description
sub Usage(){
	warn "Usage: deannotate_words.pl [options] < input > output\n";
	warn "	-help 	\tprint this help\n";
	warn "  -b      \tdisable Perl buffering.\n";
	warn "  -p      \tprint passthrough xml tag\n";
	warn "	-encoding=<type> 	\tinput and output encoding type\n";
	warn "	-collapse 	\tenable collapsing of adjacent tags\n";
	warn "	-escape 	\tescape \n";

}

if (scalar(@ARGV) < $required_params || scalar(@ARGV) > ($required_params+$optional_params) || $help) {
    &Usage();
    exit;
}

if ($bflag){ $| = 1; }

### insert here the code

while (my $line=<STDIN>){
	chomp($line);
	my ($passthrough,$trans) = ($line =~ /(^<passthrough[^>]*\/>)(.*)$/);

#parsing translation
	my @trgwords = split (/[ \t]+/, $trans);
	# eve entries contain words, eodd entries contain word-alignemnt
	for (my $i=0; $i < scalar(@trgwords); $i+=2){
		$trgwords[$i+1] =~ s/\|//g; #remove pipeline from word alignemnt
	}

#parsing passthrough
	my ($tag) = ($passthrough =~ /<passthrough[ \t]+tag=\"(.*?)\".*\/>/);
	my @tags = split(/\|\|/,$tag);
	my %xml = ();
	my %endxml = ();
	my %typexml = ();
	for (my $i=0; $i < scalar(@tags); $i++){
		my ($idx,$value,$type) = ($tags[$i] =~ /(\-?\d+)\#(.*?)\#(\d+)$/);
		
		$value =~ s/\&lt;(.+?)&gt;/$1/;
		$value =~ /^([^ \t]*)([ \t].+)?$/;
		my $mainvalue = $1;

 		if (!defined($xml{$idx})){
			$xml{$idx} = "";	
			$endxml{$idx} = "";	
			$typexml{$idx} = "";	
		}
		if ($type == CONTAINS_NONEMPTY_TEXT  || $type == NOTRANSLATE || $type == FORCETRANSLATE ){
                        $xml{$idx} .= "<$value>";
                        $endxml{$idx} = "</$mainvalue>$endxml{$idx}";
			$typexml{$idx} = $type;	
                }elsif ($type == CONTAINS_EMPTY_TEXT){
                        $xml{$idx} .= "<$value></$mainvalue>";
                        $typexml{$idx} = $type;
                }elsif ($type == SELF_CONTAINED){
                        $xml{$idx} .= "<$value />";
                        $typexml{$idx} = $type;
                }elsif ($type == OPENED_BUT_UNCLOSED){
                        $xml{$idx} .= "<$value>";
                        $typexml{$idx} = $type;
                }elsif ($type == CLOSED_BUT_UNOPENED){
                        $xml{$idx} .= "</$mainvalue>";
                        $typexml{$idx} = $type;
                }else{
                        die "Third field should have one of the following values: ",join(",",(CONTAINS_NONEMPTY_TEXT,CONTAINS_EMPTY_TEXT,SELF_CONTAINED,OPENED_BUT_UNCLOSED,CLOSED_BUT_UNOPENED,NOTRANSLATE,FORCETRANSLATE)),"\n";
                }
	}

#reconctructing the tagged output
	my $out ="";

	#adding tags not associated to any source word
        for (my $i=0; $i < scalar(@tags); $i++){
        	my ($idx,$value,$type) = ($tags[$i] =~ /(\-?\d+)\#(.*?)\#(\d+)$/);
		if ($idx == -1 && defined($xml{$idx})){
                        $out = $xml{$idx}.$endxml{$idx}." ";
		}
	}

        for (my $i=0; $i < scalar(@trgwords); $i+=2){
		my $srcidx = $trgwords[$i+1];
		if ($srcidx != -1 && defined($xml{$srcidx})){
                        $out .= $xml{$srcidx}.$trgwords[$i].$endxml{$srcidx}." ";
		}else{
			$out .= "$trgwords[$i] ";
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
        $out =~ s/>([^ ])/> $1/g;
        $out =~ s/([^ ])</$1 </g;
        $out =~ s/[ \t]+/ /g;
        $out =~ s/^[ \t]//g;
        $out =~ s/[ \t]$//g;
        $out =~ s/>[ ]+</></g;
	if ($printpassthrough){ print "$passthrough"; }
	print "$out\n";
}
