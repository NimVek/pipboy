#!/usr/bin/env python

import socket
import threading
import SocketServer

import StringIO
import pipboy

import json
import struct

import pprint

udp_port = 28000

pp = pprint.PrettyPrinter()

class PipBoyUDPHandler(SocketServer.BaseRequestHandler):
    def handle(self):
	data, socket = self.request
	try:
	    data = json.loads(data)
#	    print data
#	    print (data['cmd'] == 'autodiscover')
	    if data['cmd'] == 'autodiscover':
		response = { 'IsBusy': False, 'MachineType': 'PC' }
		response = json.dumps(response)
#		print self.client_address
		print socket.sendto(response, self.client_address)
	except Exception, e:
	    print e

class PipBoyUDPServer(SocketServer.ThreadingMixIn, SocketServer.UDPServer):
    pass

udp_server = PipBoyUDPServer(('', udp_port), PipBoyUDPHandler)
udp_thread = threading.Thread(target=udp_server.serve_forever)
udp_thread.daemon = True
udp_thread.start()

client_types = { 1: 'Drop' }

class PipBoyTCPHandler(SocketServer.StreamRequestHandler):
    def pip_send(self, channel, data):
	header = struct.pack('IB', len(data), channel)
	self.wfile.write(header)
	self.wfile.write(data)

    def pip_receive(self):
	header = self.rfile.read(5)
	size, channel = struct.unpack('IB', header)
	data = self.rfile.read(size)
	return ( channel, data )

    counter = 0
    
    def handle(self):
	while True:
	    if self.counter == 0:
		data = json.dumps( { 'lang': 'de', 'version': '1.1.30.0' })
		self.pip_send( 1, data)
	    elif self.counter == 1:
		pip = pipboy.PipBoy()
		with open('world.json', 'r') as cf:
		    world = json.load(cf)
		    pip.load_type(world)
		with open('test.dat', 'wb') as cf:
		    pip.dump_binary(cf)
		with open('test.json', 'w') as cf:
		    json.dump(pip.derefer(0),cf, indent=4, sort_keys=True)
#		    pip.load_type(world)
		tmp = StringIO.StringIO()
		pip.dump_binary(tmp)
		with open('world.dat', 'rb') as cf:
		    data = cf.read()
#		self.pip_send( 3, data)
		self.pip_send( 3, tmp.getvalue())
	    else:
		if self.counter % 5 == 0:
#		    path = "move_%04d.dat" % (( self.counter / 5) % 20)
#		    with open(path, 'rb') as cf:
#			data = cf.read()
#		    self.pip_send(3, data)
		    self.pip_send(0, '')
		else:
		    self.pip_send(0, '')
	    channel, dat = self.pip_receive()
	    if (channel == 5):
		try:
		    data = json.loads(dat)
		    pp.pprint(data)
		except Exception, e:
		    print e
		
	    self.counter += 1

tcp_server = SocketServer.TCPServer(('', 27000), PipBoyTCPHandler)
tcp_server.serve_forever()

udp_server.shutdown()
udp_server.server_close()