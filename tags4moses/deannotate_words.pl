#!/usr/bin/perl -w

#use MateCat;
use Getopt::Long;

# parameter variables
my $help = undef;
#my $enc = $MATECAT_ENC;
my $enc = UTF8;
my $collapse = 0;
my $escape = 0;

# parameter definition
GetOptions(
  "help" => \$help,
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
	warn "	-encoding=<type> 	\tinput and output encoding type\n";
	warn "	-collapse 	\tenable collapsing of adjacent tags\n";
	warn "	-escape 	\tescape \n";

}

if (scalar(@ARGV) < $required_params || scalar(@ARGV) > ($required_params+$optional_params) || $help) {
    &Usage();
    exit;
}

### insert here the code

while (my $line=<STDIN>){
	chomp($line);
#	print STDERR "line:|$line|\n";
	my ($passthrough,$trans) = ($line =~ /(^<passthrough[^>]*\/>)(.*)$/);
#$trans = "DUMMY |0| $trans";

#	print STDERR "passthough:|$passthrough|\n";
#	print STDERR "trans:|$trans|\n";

#parsing translation
	my @trgwords = split (/[ \t]+/, $trans);
	# eve entries contain words, eodd entries contain word-alignemnt
	for (my $i=0; $i < scalar(@trgwords); $i+=2){
		$trgwords[$i+1] =~ s/\|//g; #remove pipeline from word alignemnt
#		print STDERR "i:$i word:$trgwords[$i] al:",$trgwords[$i+1],"\n";
	}
#parsing passthrough
	my ($tag) = ($passthrough =~ /<passthrough[ \t]+tag=\"(.*?)\".*\/>/);
#	print STDERR "tag:|$tag|\n";
	my @tags = split(/\|\|/,$tag);
	my %xml = ();
	my %endxml = ();
	my %typexml = ();
	for (my $i=0; $i < scalar(@tags); $i++){
#		print STDERR "tag[$i]:|$tags[$i]|\n";
		my ($idx,$value,$type) = ($tags[$i] =~ /(\d+)\#(.*?)\#(\d+)$/);

		$value =~ s/\&lt;(.+?)&gt;/$1/;
		$value =~ /^([^ \t]*)([ \t].+)?$/;
		my $mainvalue = $1;

 		if (!defined($xml{$idx})){
			$xml{$idx} = "";	
			$endxml{$idx} = "";	
			$typexml{$idx} = "";	
		}
		if ($type == 0){
                        $xml{$idx} .= "<$value>";
                        $endxml{$idx} = "</$mainvalue>$endxml{$idx}";
			$typexml{$idx} = $type;	
                }elsif ($type == 1){
                        $xml{$idx} .= "<$value/>";
                        $endxml{$idx} .= "";
                        $typexml{$idx} = $type;
                }elsif ($type == 2){
                        $xml{$idx} .= "<$value></$mainvalue>";
#                        $endxml{$idx} .= "</$mainvalue>";
                        $typexml{$idx} = $type;
                }else{
                        die "Third field should have one of the following values: 0, 1, 2\n";
                }
#                print STDERR "INSIDE:$i idx:$idx type:$typexml{$idx} xml{$idx}:|$xml{$idx}| endxml{$idx}:|$endxml{$idx}|\n";

	}
#reconctructing the tagged output
	my $out ="";
        for (my $i=0; $i < scalar(@trgwords); $i+=2){
		my $srcidx = $trgwords[$i+1];
		if ($srcidx != -1 && defined($xml{$srcidx})){
                        if ($typexml{$srcidx} == 0){
                            $out .= $xml{$srcidx}.$trgwords[$i].$endxml{$srcidx}." ";
                        }elsif ($typexml{$srcidx} == 1){
                            $out .= $xml{$srcidx}.$trgwords[$i]." ";
                        }elsif ($typexml{$srcidx} == 2){
                            $out .= $xml{$srcidx}.$trgwords[$i]." ";
                        }else{
				die "Third field should have one of the following values: 0, 1, 2\n";
 			}
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
#                        print STDERR "START EXT WHILE contflag:|$contflag|\n";
#                      print STDERR "out:|$out|\n";

			while ($out =~ s/(.*?)(<\/[ ]*([^ >]+?)[ ]*>[ \t]*<(([^ \t>\/]+?)([ \t][^>]*>|>)))//){

				$newout .= " $1 ";
				my $endtag = $3;
				my $starttag = $5;
#                                print STDERR "endtag:|$endtag| starttag:|$starttag|\n";
				if ($endtag eq $starttag){
					$contflag=1;
				}
				else
				{
					$newout .= " $2 ";
				}
#                	        print STDERR "newout:|$newout|\n";
#                        	print STDERR "out:|$out|\n";
			}
			$newout .= " $out ";
			$out = $newout;
#                	print STDERR "newout:|$newout|\n";
#                	print STDERR "out:|$out|\n";
#                        print STDERR "END EXT WHILE contflag:|$contflag|\n";
		}
		#$newout .= " $out ";
		#$out = $newout;
	}

# escaping (or not) some characters
	if ($escape){
		$out =~ s/</&lt;/g;
		$out =~ s/>/&gt;/g;
	}
	else{
		$out =~ s/\&amp;/\&/g;
		$out =~ s/\&quot;/\"/g;
	}

# removing index of tags
#        $out =~ s/(<\/?)([^> ]+)_\d+/$1$2/g;

# removing double spaces and spaces at the beginning and end of the line
        $out =~ s/>([^ ])/> $1/g;
        $out =~ s/([^ ])</$1 </g;
        $out =~ s/[ \t]+/ /g;
        $out =~ s/^[ \t]//g;
        $out =~ s/[ \t]$//g;
        $out =~ s/>[ ]+</></g;
	print "$out\n";
}
