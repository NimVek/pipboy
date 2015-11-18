#!/usr/bin/env python

import json
import pipboy

import cmd

import logging
logging.basicConfig(level=logging.INFO)

class PipBoyClient(cmd.Cmd):
    def __init__(self):
	cmd.Cmd.__init__(self)
	self.prompt = 'PipBoyClient: '
	self.model = pipboy.Model()
	self.model.register('update', self.listen_update)

    def listen_update( self, ids):
	for item in ids:
	    print self.model.get_path(item)
	    print self.model.get_item(item)

    def emptyline(self):
	pass

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

    def do_savejson( self, line):
	data = self.client.pip.derefer(0)
	with open(line, 'w') as outfile:
	    json.dump(data, outfile, indent=4, sort_keys=True)

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
    PipBoyClient().cmdloop()