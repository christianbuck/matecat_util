#!/usr/bin/perl -w

#use MateCat;
use Getopt::Long;

# parameter variables
my $help = undef;
#my $enc = $MATECAT_ENC;
my $enc = UTF8;
my $bflag = 0;

# parameter definition
GetOptions(
  "help" => \$help,
  "b" => \$bflag,
  "encoding=s" => \$enc,
) or exit(1);

my $required_params = 0; # number of required free parameters
my $optional_params = 0; # maximum number of optional free parameters

# command description
sub Usage(){
	warn "Usage: handle_span_class.pl [options] < input > output\n";
	warn "	-help 	\tprint this help\n";
	warn "	-encoding=<type> 	\tinput and output encoding type\n";
}

if (scalar(@ARGV) < $required_params || scalar(@ARGV) > ($required_params+$optional_params) || $help) {
    &Usage();
    exit;
}

### insert here the code
if ($bflag){ $| = 1; }

my $forcescore = 100;
while (my $line=<STDIN>){
	chomp($line);
##	print STDERR "line:|$line|\n";
	while ($line =~ /<span ([^>]*?)class=\"notranslate\"([^>]*?>)(.+?)<\/span>/){
		my $tagbef=$1;
		my $tagaft=$2;
		my $word=$3;
		my $textbef = $`;
		my $textaft = $';
		my $trans = $word;
		$trans =~ s/^\s*//;	
		$trans =~ s/\s*$//;	
		my $spantag = "<notranslate ${tagbef}target=\"${trans}\" pr=\"$forcescore\"${tagaft}${word}</notranslate>";
		$spantag =~ s/\s+>/>/g;
		$line = $textbef.$spantag.$textaft;
	}
	while ($line =~ /<span ([^>]*?)class=\"forcetranslate\" ([^>]*?)translation=\"([^\"]*)\"([^>]*?>)(.+?)<\/span>/){
                my $tagbef=$1;
                my $tagmid=$2;
                my $trans=$3;
                my $tagaft=$4;
                my $word=$5;
                my $textbef = $`;
                my $textaft = $';
		my $spantag = "<forcetranslate ${tagbef}target=\"${trans}\" pr=\"$forcescore\" ${tagmid}${tagaft}${word}</forcetranslate>";
		$spantag =~ s/\s+>/>/g;
		$line = $textbef.$spantag.$textaft;
	}
	print "$line\n";
}
