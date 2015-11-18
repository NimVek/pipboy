#!/usr/bin/env python

import pipboy

import cmd

import logging
logging.basicConfig(level=logging.DEBUG)

class PipBoyServer(cmd.Cmd):
    logger = logging.getLogger('PipBoyServer')
    def __init__(self):
	cmd.Cmd.__init__(self)
	self.prompt = 'PipBoyServer: '
	self.model = pipboy.Model()

    def emptyline(self):
	pass

    def do_start( self, line):
	self.client = pipboy.TCPServer( self.model)
	self.client.start()

    def do_load(self, line):
	with open(line, 'rb') as stream:
	    self.model.load(pipboy.TCPFormat.load(stream))

    def do_set(self, line):
	(path, value,) = line.split(' ')
	self.logger.debug("path = " + path)
	self.logger.debug("value = " + value)


    _LOGLEVEL = { 'CRITICAL': logging.CRITICAL,
		 'ERROR': logging.ERROR,
		 'WARNING': logging.WARNING,
		 'INFO': logging.INFO,
		 'DEBUG': logging.DEBUG,
		 'NOTSET': logging.NOTSET
		}

    def complete_loglevel( self, text, line, begidx, endidx):
	return [i for i in self._LOGLEVEL if i.startswith(text)]

    def do_loglevel( self, line):
	logging.getLogger().setLevel( self._LOGLEVEL[line])

    def do_EOF(self, line):
	return True

if __name__ == '__main__':
    PipBoyServer().cmdloop()