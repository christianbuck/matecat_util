#!/usr/bin/perl

use URI::Escape;

while (<STDIN>) {
  print uri_escape($_), "\n";
}
