#!/bin/bash

function die() { echo "$@" >&2; exit 1; }
set -o pipefail  # safer pipes

input="$1"
[ -e "$input" ] || die "usage: $0 input-file"

vimdiff "$input" \
  <(cat "$input" | ./annotate_words.py \
    | perl -lne 's/^(<[^>]+>)//; my $hide = $1;my $i=0; my @out = (); foreach my $tok (split / /) { push @out, "$tok |$i|"; $i++} print $hide, join(" ", @out);' \
    | ./deannotate_words.pl --collapse --force-insert-all --avoid-duplicate-insertion \
   )
