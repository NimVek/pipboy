#!/usr/bin/env python

import struct

import socket
import json
import StringIO
import threading

import logging
import pprint
pp = pprint.PrettyPrinter()

TCP_PORT = 27000
UDP_PORT = 28000

class PipBoy(object):
    def _clear(self):
	self._path = {}
	self._items = {}

    def __init__( self ):
	self.logger = logging.getLogger('pipboy.PipBoy')
	self._clear()

    def _parse_bool( self, stream ):
	(val,) = struct.unpack('<B', stream.read(1))
	val = [False,True][val]
	return val

    def _parse_sint_8( self, stream ):
	(val,) = struct.unpack('<b', stream.read(1))
	return val

    def _parse_uint_8( self, stream ):
	(val,) = struct.unpack('<B', stream.read(1))
	return val

    def _parse_sint_32( self, stream ):
	(val,) = struct.unpack('<i', stream.read(4))
	return val

    def _parse_uint_32( self, stream ):
	(val,) = struct.unpack('<I', stream.read(4))
	return val

    def _parse_float_32( self, stream ):
	(val,) = struct.unpack('<f', stream.read(4))
	return val

    def _parse_unpack( self, stream, size, unpack ):
	(val,) = struct.unpack(unpack, stream.read(size))
	return val

    def _parse_cstr( self, stream ):
	buf = bytearray()
	while True:
	    b = stream.read(1)
	    if b == '\x00':
		return str(buf)
	    else:
		buf.append(b)

    def _update_path( self, _parent, name, _id):
	self._path[_id] = ( name, _parent )

    def _parse_list( self, stream, _id ):
	val = []
	(_count,) = struct.unpack('<H', stream.read(2))
	for i in range(0,_count):
	    (tmp,) = struct.unpack('<I', stream.read(4))
	    val.append(tmp)
	    self._update_path(_id, "%u" % i, tmp)
	return val

    def _parse_dict( self, stream, _id ):
	val = {}
	(_count,) = struct.unpack('<H', stream.read(2))
	for i in range(0,_count):
	    (ref,) = struct.unpack('<I', stream.read(4))
	    attribute = self._parse_cstr(stream)
	    val[attribute] = ref
	    self._update_path(_id, attribute, ref)
	(_unknown,) = struct.unpack('<H', stream.read(2))
	return val

    def _get_path( self, _id ):
	if _id in self._path:
	    entry = self._path[_id]
	    parent_path = self._get_path( entry[1] )
	    if parent_path:
		return "%s.%s" % (parent_path, entry[0] )
	    else:
		return entry[0]

    def derefer( self, _id ):
	result = self._items[_id]
	if type(result) == list:
	    result = [ self.derefer(v) for v in result ]
	elif type(result) == dict:
	    result = { k: self.derefer(v) for k, v in result.items() }
	return result

    def _update_item( self,_id, val):
	self._items[_id] = val
	current_path = self._get_path( _id)
	if current_path:
	    self.logger.info("%s:\n0x%08x: %s" % (current_path, _id, val))
	else:
	    self.logger.info("0x%08x: %s" % (_id, val))
#	if _id == 0:
#	    with open('world.json', 'w') as outfile:
#		json.dump( derefer(_id), outfile, indent=4, sort_keys=True)

    def update_binary( self, stream ):
	while True:
	    typ = stream.read(1)
	    if not typ: break
	    (typ,) = struct.unpack('<B', typ)
	    (_id,) = struct.unpack('<I', stream.read(4))
	    if typ == 0: # confirmed bool
		val = self._parse_bool(stream)
	    elif typ == 1:
		val = self._parse_unpack(stream, 1, '<b')
#		val = self._parse_sint_8(stream)
	    elif typ == 2:
		val = self._parse_unpack(stream, 1, '<B')
#		val = self._parse_uint_8(stream)
	    elif typ == 3:
		val = self._parse_unpack(stream, 4, '<i')
#		val = self._parse_sint_32(stream)
	    elif typ == 4: # confirmed uint_32
		val = self._parse_unpack(stream, 4, '<I')
#		val = self._parse_uint_32(stream)
	    elif typ == 5: # confirmed float
		val = self._parse_unpack(stream, 4, '<f')
#		val = self._parse_float_32(stream)
	    elif typ == 6:
		val = self._parse_cstr(stream)
	    elif typ == 7:
		val = self._parse_list(stream, _id)
	    elif typ == 8:
		val = self._parse_dict(stream, _id)
	    else:
		print "Error Unknown Typ %d" % typ
		break
	    self._update_item(_id, val)

    def load_binary ( self, stream):
	self._clear()
	self.update_binary()

    def _dump_cstr( self, stream, string ):
	stream.write(string)
	stream.write('\x00')

    def _dump_head( self, stream, _id, typ):
	stream.write(struct.pack('<BI', typ, _id))

    def _dump( self, stream, _id, typ, value ):
	self._dump_head(stream,_id, typ)
	stream.write(value)

    def _dump_pack( self, stream, _id, typ, pack, value ):
	self._dump( stream, _id, typ, struct.pack( pack, value))

    def _dump_bool( self, stream, _id, item ):
	self._dump_pack ( stream, _id, 0, '<B', 1 if item else 0 )

    def _dump_int( self, stream, _id, item ):
	if item < 0:
	    if item < -128:
		typ = ( 3, '<i')
	    else:
		typ = ( 1, '<b')
	else:
	    if item > 127:
		typ = ( 4, '<I')
	    else:
		typ = ( 2, '<b')
	self._dump_pack( stream, _id, typ[0], typ[1], item)

    def _dump_float( self, stream, _id, item ):
	self._dump_pack ( stream, _id, 5, '<f', item )

    def _dump_str( self, stream, _id, item ):
	self._dump_head(stream, _id, 6)
	self._dump_cstr(stream, item)

    def _dump_list( self, stream, _id, item ):
	self._dump_head(stream, _id, 7)
	stream.write(struct.pack('<H', len(item) ))
	for val in item:
	    stream.write(struct.pack('<I', val))

    def _dump_dict( self, stream, _id, item ):
	self._dump_head(stream, _id, 8)
	stream.write(struct.pack('<H', len(item) ))
	for key, val in item.items():
	    stream.write(struct.pack('<I', val))
	    self._dump_cstr(stream, key)
	stream.write(struct.pack('<H', 0 ))

    def dump( self, stream, start = 0, complete = True ):
	item = self._items[start]
	if type(item) == bool:
	    result = self._dump_bool(stream, start, item)
	elif type(item) == int:
	    result = self._dump_int(stream, start, item)
	elif type(item) == float:
	    result = self._dump_float(stream, start, item)
	elif type(item) == str:
	    result = self._dump_str(stream, start, item)
	elif type(item) == list:
	    if complete:
		for child in item:
		    self.dump_binary(stream, child, complete)
	    result = self._dump_list(stream, start, item)
	elif type(item) == dict:
	    if complete:
		for child in item.values():
		    self.dump_binary(stream, child, complete)
	    result = self._dump_dict(stream, start, item)

    def _convert_str(self, string):
	if type(string) == unicode:
	    return string.encode('utf8')
	else:
	    return string

    def _load_type(self, item ):
	_id = len(self._items)
	self._items[_id] = item
	self._convert_str(item)
	if type(item) == unicode:
	    self._items[_id] = item.encode('utf8')
	elif type(item) == list:
	    self._items[_id] = [ self._load_type(child) for child in item ]
	elif type(item) == dict:
	    self._items[_id] = { self._convert_str(k): self._load_type(v) for k,v in item.items() }
	return _id

    def load_type( self, item ):
	self._clear()
	self._load_type( item )
	inventory = self._items[0]['Inventory']
	inventory = self._items[inventory]
	sorted_ids = inventory['sortedIDS']
	sorted_ids = self._items[sorted_ids]
	print "START"
	print len(sorted_ids)
	all_ids = []
	for k,v in inventory.items():
	    tmp = self._items[v]
	    if k.isdigit():
		all_ids += tmp
		print len(tmp)
	sorted_i = []
	for i in all_ids:
	    _id = len(self._items)
	    self._items[_id] = i
	    sorted_i.append(_id)
	sorted_ids = inventory['sortedIDS']
	self._items[sorted_ids] = sorted_i
	print "DONE"

class UDPClient(object):
    @staticmethod
    def discover():
	udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, True)
	udp_socket.settimeout(5)
	udp_socket.sendto(json.dumps({'cmd': 'autodiscover'}), ('<broadcast>', UDP_PORT))
	result = []
	timeout = False
	while not timeout:
	    try:
		received, fromaddr = udp_socket.recvfrom(1024)
		data = json.loads(received)
		data['IpAddr'] = fromaddr[0]
		result.append(data)
	    except socket.timeout, e:
		timeout = True
	return result

class TCPBase(object):
    def __init__( self ):
	super(TCPBase, self).__init__()
	self.logger = logging.getLogger('pipboy.TCPBase')

    socket = None

    def receive(self):
	header = self.socket.recv(5)
	size, channel = struct.unpack('<IB', header)
	data = ''
	while size > 0:
	    tmp = self.socket.recv(size)
	    data += tmp
	    size -= len(tmp)
	return ( channel, data )

    def send(self, channel, data):
	header = struct.pack('<IB', len(data), channel)
	self.socket.send(header)
	self.socket.send(data)

    serve = False
    thread = None

    def start(self):
	self.thread = threading.Thread(target=self._run, name=type(self).__name__)
	self.thread.daemon = True
	self.thread.start()
    
    def pre():
	pass

    def run():
	pass

    def post():
	if socket:
	    socket.close()

    def _run(self):
	self.pre()
	self.serve = True
	while self.serve:
	    self.run()
	self.post()

    def stop(self):
	self.serve = False
	thread.join()

class TCPClient(TCPBase):
    def __init__( self ):
	super(TCPClient, self).__init__()
	self.logger = logging.getLogger('pipboy.TCPClient')
	self.pip = PipBoy()

    server = None

    def pre(self):
	self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	self.socket.connect((self.server, TCP_PORT))

    def run(self):
	(channel, data) = self.receive()
	if channel == 0:
	    pass
	elif channel == 1:
	    pass
	elif channel == 3:
	    stream = StringIO.StringIO(data)
	    self.pip.update_binary( stream )
	else:
	    self.logger.warn("Error Unknown Channel %d" % ( channel))
	self.send( 0, '')
