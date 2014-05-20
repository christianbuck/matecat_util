#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys, logging, os
import codecs, subprocess, select, re, logging

from ConfigParser import SafeConfigParser

logging.basicConfig(level=logging.INFO)

def read_file(fn):
        """
        Read a list of sentences from a file.
        """
        try:
                return [line.strip() for line in open(fn)]
        except IOError:
                sys.stderr.write("Could not open file "+fn+"\n")
                sys.exit()

def write_to_file(fn, output):
	"""
	Write output to file named fn.
	"""
	f = open(fn, 'w')
	f.write(output)
	f.close()

class Decoder_Deterministic:
        def __init__(self, parser):
                """
                Start a new decoder with the specified command line arguments.
                """
                self.parser = parser

		self.source = parser.get('decoder', 'source')
		self.target = parser.get('decoder', 'target')
		self.verbosity = 0
		try:
			self.verbosity = int(parser.get('decoder', 'verbosity'))
		except:
			self.verbosity = 0

		self.source_list = read_file(self.source)
		self.target_list = read_file(self.target)
		self.source_hash = {}

		i = 0
		while i < len(self.source_list):
	        	if self.verbosity > 0: logging.info("INSERT:|"+self.source_list[i]+"|")
			if not self.source_list[i] in self.source_hash: 
				self.source_hash[self.source_list[i]] = i
			i += 1

        def communicate(self, in_line):
                """
                Return output and error of the decoder for the given input.
                """
		err = []
		output = ""
	        logging.info("Decoder_Deterministic:|"+in_line+"|")
                if in_line in self.source_hash:
			if self.verbosity > 0: logging.info("Match:|"+in_line+"|")
			output = self.target_list[self.source_hash[in_line]]
		else:
	        	if self.verbosity > 0: logging.info("NO Match:|"+in_line+"|")
		return output, "".join(err)


class Decoder_Moses:
	"""
	Opens an instance of the decoder specified in path as a subprocess 
	and handles communication, i.e. sending input and parsing output.
	"""
        def __init__(self, parser):
                """
                Start a new decoder with the specified command line arguments.
                """
                self.parser = parser

	        # set default parameters (if needed)
	        default_decoder_options = "-xml-input inclusive"
	        default_decoder_options = default_decoder_options + " -no-cache"
	        try:
	                self.parser.get('decoder', 'options')
	        except:
	                self.parser.set('decoder', 'options', '')
                try:
                        verbosity = self.parser.get('decoder', 'verbosity')
                        logging.info("Forcing Moses verbosity to 1")
                        if int(verbosity) < 1:
                                self.parser.set('decoder', 'verbosity', '1')
                except:
                        logging.info("Setting Moses verbosity to 1")
                        self.parser.set('decoder', 'verbosity', '1')

	        decoder_options = self.parser.get('decoder', 'options')
	        if decoder_options:
	                decoder_options = decoder_options + " "
	        decoder_options = decoder_options + default_decoder_options
                decoder_options = decoder_options + " " + self.parser.get('decoder', 'showweightsflag')
                decoder_options = re.sub(r"^\s+",'',decoder_options)
                decoder_options = re.sub(r"\s+$",'',decoder_options)
	        decoder_options_list = decoder_options.split(' ')

	        logging.info("MAIN decoder_options:|"+decoder_options+"|")
	        logging.info("MAIN decoder_options_list|"+str(decoder_options_list)+"|")

		self.path = parser.get('decoder', 'path')
	        decoder_args = ("-f", parser.get('decoder', 'ini'),
	                        "-v", parser.get('decoder', 'verbosity'))
	        logging.info("MAIN decoder_path:|"+str(self.path)+"|")
	        logging.info("MAIN decoder_args:|"+str(decoder_args)+"|")

	        self.decoder_args_list = list(decoder_args)
	        self.decoder_args_list.extend(decoder_options_list)
	        decoder_args = tuple(self.decoder_args_list)

                logging.info("DECODER_CALL:|"+self.path+' '+" ".join(self.decoder_args_list)+"|")

                if not self.parser.get('decoder', 'showweightsflag') == "":
                        self.log_decoder = open(os.devnull, 'w')
                else:
                        self.log_decoder = subprocess.STDOUT

                self.decoder = subprocess.Popen([self.path]+self.decoder_args_list,
                        stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE,
                        stderr=self.log_decoder,
                        shell=False)

#pattern to match in order to know that all output related to one sentence has been produced
		self.out_signal_pattern = re.compile("^BEST TRANSLATION:\s*")

#pattern to match in order to know that the output related to one sentence starts
		self.in_signal_pattern = re.compile("Translating line [0-9]+")
	
#pattern to match in order to know that the output of the show-weights has been produced
                self.showweights_signal_pattern = re.compile("^$")

        def show_weights(self):
                out = ""
                err = []
                self.log_t2s = open(os.devnull, 'w')
                while True:
                        line = self.decoder.stdout.readline().strip()
                        out += line + "\n"
                        if self.showweights_signal_pattern.search(line):
                                break   
                        self.log_t2s = open(os.devnull, 'w')
		out = re.sub(r"\n+","\n",out)
                return out,"".join(err)

	def communicate(self, in_line):
		"""
		Return output and error of the decoder for the given input.
		"""
		self.decoder.stdin.write(in_line+'\n')
		err = []

                while True:
                        line = self.decoder.stdout.readline().strip()
			if self.in_signal_pattern.search(line):
				err.append(line+'\n')
				break
			
		while True:
			line = self.decoder.stdout.readline().strip()
			if self.out_signal_pattern.search(line):
				# err line before output
				err.append(line+'\n')
				out = line
				out = re.sub (self.out_signal_pattern, '', out)
				out = re.sub ("\s+[[01]*\]\s+\[total=[-.0-9]+\].+$", '', out)
				out = re.sub ("(\|UNK)+",'',out)

				break
			else:
				if not "cblm::Evaluate:" in line:
					logging.debug("DECODER_ERR: "+line)
					err.append(line+'\n')

		return out, "".join(err)

class Decoder_Moses_nbest:
        """
        Opens an instance of the decoder specified in path as a subprocess 
        and handles communication, i.e. sending input and parsing output.
        """
        def __init__(self, parser):
                """
                Start a new decoder with the specified command line arguments.
                """
                self.parser = parser

                # set default parameters (if needed)
                default_decoder_options = "-xml-input inclusive"
                default_decoder_options = default_decoder_options + " -no-cache false"
                try:
                        self.parser.get('decoder', 'options')
                except:
                        self.parser.set('decoder', 'options', '')
                try:
                        verbosity = self.parser.get('decoder', 'verbosity')
                	logging.info("Forcing Moses verbosity to 1")
                        if int(verbosity) < 1:
				self.parser.set('decoder', 'verbosity', '1')
                except:
                	logging.info("Setting Moses verbosity to 1")
                        self.parser.set('decoder', 'verbosity', '1')

                decoder_options = self.parser.get('decoder', 'options')
                if decoder_options:
                        decoder_options = decoder_options + " "
                decoder_options = decoder_options + default_decoder_options
                decoder_options = decoder_options + " " + self.parser.get('decoder', 'showweightsflag')
                decoder_options = re.sub(r"^\s+",'',decoder_options)
                decoder_options = re.sub(r"\s+$",'',decoder_options)
                decoder_options_list = decoder_options.split(' ')

                logging.info("MAIN decoder_options:|"+decoder_options+"|")
                logging.info("MAIN decoder_options_list|"+str(decoder_options_list)+"|")

                self.path = parser.get('decoder', 'path')
                decoder_args = ("-f", parser.get('decoder', 'ini'),
                                "-v", parser.get('decoder', 'verbosity'))
                logging.info("MAIN decoder_path:|"+str(self.path)+"|")
                logging.info("MAIN decoder_args:|"+str(decoder_args)+"|")

                self.decoder_args_list = list(decoder_args)
                self.decoder_args_list.extend(decoder_options_list)
                decoder_args = tuple(self.decoder_args_list)

                logging.info("DECODER_CALL:|"+self.path+' '+" ".join(self.decoder_args_list)+"|")

                if not self.parser.get('decoder', 'showweightsflag') == "":
                        self.log_decoder = open(os.devnull, 'w')
                else:
                        self.log_decoder = subprocess.STDOUT

                self.decoder = subprocess.Popen([self.path]+self.decoder_args_list,
                        stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE,
                        stderr=self.log_decoder,
                        shell=False)

#pattern to match in order to know that all output related to one sentence has been produced
                self.out_signal_pattern = re.compile("Line [0-9]+: Translation took [0-9\.]+ seconds total")

#pattern to match in order to know that the output related to one sentence starts
                self.in_signal_pattern = re.compile("Translating line [0-9]+")

#pattern to match in order to know that the output of the show-weights has been produced
                self.showweights_signal_pattern = re.compile("^$")

        def show_weights(self):
                out = ""
                err = []
                self.log_t2s = open(os.devnull, 'w')
                while True:
                        line = self.decoder.stdout.readline().strip()
                        out += line + "\n"
                        if self.showweights_signal_pattern.search(line):
                                break
                        self.log_t2s = open(os.devnull, 'w')
                out = re.sub(r"\n+","\n",out)
                return out,"".join(err)

        def communicate(self, in_line):
                """
                Return output and error of the decoder for the given input.
                """
                self.decoder.stdin.write(in_line+'\n')
                err = []
                nbest = []

                while True:
                        line = self.decoder.stdout.readline().strip()
                        if self.in_signal_pattern.search(line):
                                err.append(line+'\n')
                                break

                while True:
                        line = self.decoder.stdout.readline().strip()
                        if not self.out_signal_pattern.search(line):
                                # err line before output
                                if "|||" in line:
                                        nbest.append(line)
                                else:
                                        err.append(line+'\n')
                        else:
                                break

                return nbest, "".join(err)

def usage():
        """
        Prints script usage.
        """
        sys.stderr.write("./decoder.py .....\n")


if __name__ == "__main__":
        if not len(sys.argv) == 2:
                usage()
                sys.exit()
        else:
                # parse config file
                parser = SafeConfigParser()
                parser.read(sys.argv[1])

#### TO IMPLEMENT A CASE STUDY


