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
	warn "Usage: template.pl [-help] [--encoding=type]\n";
	warn "	-help 	\tprint this help\n";
	warn "	-encoding=<type> 	\tinput and output encoding type\n";

}

if (scalar(@ARGV) < $required_params || scalar(@ARGV) > ($required_params+$optional_params) || $help) {
    &Usage();
    exit;
}

### insert here the code

while (my $line=<STDIN>){
	chomp($line);
	print STDERR "line:|$line|\n";
	my ($passthrough,$trans) = ($line =~ /(^<passthrough[^>]*\/>)(.*)$/);
	
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
	for (my $i=0; $i < scalar(@tags); $i++){
#		print STDERR "tag[$i]:|$tags[$i]|\n";
		my ($idx,$value) = ($tags[$i] =~ /(\d+)\#(.*?)$/);
		my $j = 0;
		my @values = ();
		while ($value =~ s/\&lt;(.+?)&gt;//){
			$values[$j] = $1;
			$values[$j] =~ /^([^ \t]*)([ \t].+)?$/;
			$mainvalues[$j] = $1; 
#			print STDERR "idx:$idx val:|$value| value:|$value| j:$j values[$j]:|$values[$j]| mainvalues[$j]:|$mainvalues[$j]|\n";
			$j++;
		}
		#$value =~ s/\&gt;/\>/g;
		#$value =~ s/\&lt;/\</g;
		#$value =~ s/\&quot;/\"/g;
		$xml{$idx} = "";
		$endxml{$idx} = "";
		for ($j=0;$j < scalar(@values); $j++){
			$xml{$idx} .= "<$values[$j]>";
			$endxml{$idx} .= "</".$mainvalues[scalar(@values)-$j-1].">";
		}
#		print STDERR "i:$i idx:$idx xml{$idx}:|$xml{$idx}| endxml{$idx}:|$endxml{$idx}|\n";

	}
#reconctructing the tagged output
	my $out ="";
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
			while ($out =~ s/(.*?)<\/([^ \t]+?)>[ \t]*<(([^ \t]+?)([ \t]|>)[^^>]*)>//){
				$newout .= $1;
				my $endtag = $2;
				my $starttag = $4;
				if ($endtag eq $starttag){
					$contflag=1;
				}
				else
				{
					$newout .= $&;
				}
			}
		}
		$newout .= $out;
		$out = $newout;
	}

# escaping (or not) some characters
	if ($escape){
		$out =~ s/\&amp;/\&/g;
		$out =~ s/\&quot;/\"/g;
	}
	else{
		$out =~ s/</&lt;/g;
		$out =~ s/>/&gt;/g;
	}
	print "$out\n";
}
