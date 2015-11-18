#!/usr/bin/env python

import pipboy

import cmd

import logging
logging.basicConfig(level=logging.INFO)

class PipBoyMitM(cmd.Cmd):
    def __init__(self):
	cmd.Cmd.__init__(self)
	self.prompt = 'PipBoyMitM: '
	self.model = pipboy.Model()
	self.model.register('update', self.listen_update)

    def emptyline(self):
	pass

    def listen_update( self, ids):
	print ids

    def do_discover( self, line):
	for server in pipboy.UDPClient.discover():
	    print server

    def _connect( self, server):
	self.client = pipboy.TCPClient( self.model)
	self.client.server = server
	self.client.start()

    def do_connect( self, line):
	self._connect( line )

    def do_autoconnect( self, line):
	for server in pipboy.UDPClient.discover():
	    if not server['IsBusy']:
		self._connect(server['IpAddr'])

    def do_start( self, line):
	self.client = pipboy.TCPServer( self.model)
	self.client.start()

    def do_load(self, line):
	with open(line, 'rb') as stream:
	    self.model.load(pipboy.TCPFormat.load(stream))

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
    PipBoyMitM().cmdloop()
