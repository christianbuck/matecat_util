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
my $bflag = 0;
my $forcescore = 10;
my $mosesformat = 0;

# parameter definition
GetOptions(
  "help" => \$help,
  "b" => \$bflag,
  "moses" => \$mosesformat,
  "forcescore=i" => \$forcescore,
) or exit(1);

my $required_params = 0; # number of required free parameters
my $optional_params = 3; # maximum number of optional free parameters

# command description
sub Usage(){
	warn "Usage: deannotate_words.pl [options] < input > output\n";
	warn "	-help 	\tprint this help\n";
        warn "  -b      \tdisable Perl buffering.\n";
	warn "	-moses 	\ttransform xml tags (notranslate and forcetranslate) into the corresponding Moses format (xmp-input) (default is 0)\n";
	warn "	-forcescore=<value>	\tset the probability of the forced translation (default is 10)\n";
}

if (scalar(@ARGV) < $required_params || scalar(@ARGV) > ($required_params+$optional_params) || $help) {
    &Usage();
    exit;
}

if ($bflag){ $| = 1; }
#if ($mosesflag){ $mosesformat = 1; }

### insert here the code

while (my $line=<STDIN>){
	chomp($line);
	my ($passthrough,$text) = ($line =~ /(^<passthrough[^>]*\/>)(.*)$/);

#parsing text
	my @words = ();
	# even entries contain words, eodd entries contain word-alignemnt
	my $i = 0;
	foreach my $word (split (/[ \t]+/, $text)){
		push @words, ($word,$i);
		$i+=1;
	}

#parsing passthrough
	my ($tag) = ($passthrough =~ /<passthrough[ \t]+tag=\"(.*?)\".*\/>/);
	my @tags = split(/\|\|/,$tag);
	my %xml = ();
	my %endxml = ();
	my %typexml = ();
	for (my $i=0; $i < scalar(@tags); $i++){
		#my ($idx,$value,$type) = ($tags[$i] =~ /(\d+)\#(.*?)\#(\d+)$/);
		my ($idx,$value,$type,$spacetype) = ($tags[$i] =~ /(\d+)\#(.*?)\#(\d+)\#(\-?\d+)$/);

		$value =~ s/\&lt;(.+?)&gt;/$1/;
		$value =~ /^([^ \t]*)([ \t].+)?$/;
		my $mainvalue = $1;

 		if (!defined($xml{$idx})){
			$xml{$idx} = "";	
			$endxml{$idx} = "";	
			$typexml{$idx} = -1;	
		}
		if ($type == NOTRANSLATE || $type == FORCETRANSLATE){
                        $xml{$idx} = "<$value>";
                        $endxml{$idx} = "</$mainvalue>$endxml{$idx}";
			$typexml{$idx} = $type;	
                }
	}

#reconctructing the tagged output
	my $out ="";
        for (my $i=0; $i < scalar(@words); $i+=2){
		my $srcidx = $words[$i+1];

		if ($srcidx != -1 && defined($xml{$srcidx}) && 
			($typexml{$srcidx} == NOTRANSLATE || $typexml{$srcidx} == FORCETRANSLATE)){
                        $out .= $xml{$srcidx}.$words[$i].$endxml{$srcidx}." ";
		}else{
			$out .= "$words[$i] ";
		}
	}

# collapse tags
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

# removing index of tags
        $out =~ s/(<\/?)([^> ]+)_\d+/$1$2/g;

# not escaping some characters
        $out =~ s/\&amp;/\&/g;
        $out =~ s/\&quot;/\"/g;


	if ($mosesformat){
		while ($out =~ /<span ([^>]*?)class=\"notranslate\"([^>]*?>)(.+?)<\/span>/){
			my ($tagbef, $tagaft, $word, $trans) = ($1,$2, $3, $3);
			my ($textbef, $textaft) = ($`,$');
			$trans =~ s/^\s*//;	
			$trans =~ s/\s*$//;	
			my $spantag = "<notranslate ${tagbef}english=\"${trans}\" pr=\"$forcescore\"${tagaft}${word}</notranslate>";
			$spantag =~ s/\s+>/>/g;
			$out = $textbef.$spantag.$textaft;
		}
		while ($out =~ /<span ([^>]*?)class=\"forcetranslate\" ([^>]*?)translation=\"([^\"]*)\"([^>]*?>)(.+?)<\/span>/){
	                my ($tagbef, $tagmid, $trans, $tagaft, $word) = ($1,$2,$3,$4,$5);
        	        my ($textbef, $textaft) = ($`,$');

			my $spantag = "<forcetranslate ${tagbef}english=\"${trans}\" pr=\"$forcescore\" ${tagmid}${tagaft}${word}</forcetranslate>";
			$spantag =~ s/\s+>/>/g;
			$out = $textbef.$spantag.$textaft;
		}
	}

# removing double spaces and spaces at the beginning and end of the line
        $out =~ s/>([^ ])/> $1/g;
        $out =~ s/([^ ])</$1 </g;
        $out =~ s/[ \t]+/ /g;
        $out =~ s/^[ \t]//g;
        $out =~ s/[ \t]$//g;
        $out =~ s/>[ ]+</></g;
	print "$passthrough$out\n";
}
