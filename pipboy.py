#!/usr/bin/env python

import struct

import socket
import json
import StringIO
import threading
import SocketServer
import cmd
import readline
import re
import time

import logging

TCP_PORT = 27000
UDP_PORT = 28000


class TCPFormat(object):
    logger = logging.getLogger("pipboy.TCPFormat")

    @staticmethod
    def __load_bool(stream):
        (val, ) = struct.unpack('<B', stream.read(1))
        val = [False, True][val]
        return val

    @staticmethod
    def __load_native(stream, size, unpack):
        (val, ) = struct.unpack(unpack, stream.read(size))
        return val

    @staticmethod
    def __load_cstr(stream):
        buffer = bytearray()
        while True:
            byte = stream.read(1)
            if byte == '\x00':
                return str(buffer)
            else:
                buffer.append(byte)

    @staticmethod
    def __load_list(stream):
        value = []
        (_count, ) = struct.unpack('<H', stream.read(2))
        for i in range(0, _count):
            (tmp, ) = struct.unpack('<I', stream.read(4))
            value.append(tmp)
        return value

    @staticmethod
    def __load_dict(stream):
        value = {}
        (_count, ) = struct.unpack('<H', stream.read(2))
        for i in range(0, _count):
            (ref, ) = struct.unpack('<I', stream.read(4))
            attribute = TCPFormat.__load_cstr(stream)
            value[attribute] = ref
        (_count, ) = struct.unpack('<H', stream.read(2))
        for i in range(0, _count):
            (ref, ) = struct.unpack('<I', stream.read(4))
        return value

    @staticmethod
    def load(stream):
        items = []
        while True:
            typ = stream.read(1)
            if not typ: break
            (typ, ) = struct.unpack('<B', typ)
            (_id, ) = struct.unpack('<I', stream.read(4))
            if typ == 0:  # confirmed bool
                value = TCPFormat.__load_bool(stream)
            elif typ == 1:
                value = TCPFormat.__load_native(stream, 1, '<b')
            elif typ == 2:
                value = TCPFormat.__load_native(stream, 1, '<B')
            elif typ == 3:
                value = TCPFormat.__load_native(stream, 4, '<i')
            elif typ == 4:  # confirmed uint_32
                value = TCPFormat.__load_native(stream, 4, '<I')
            elif typ == 5:  # confirmed float
                value = TCPFormat.__load_native(stream, 4, '<f')
            elif typ == 6:
                value = TCPFormat.__load_cstr(stream)
            elif typ == 7:
                value = TCPFormat.__load_list(stream)
            elif typ == 8:
                value = TCPFormat.__load_dict(stream)
            else:
                TCPFormat.logger.error("Unknown Typ %d" % typ)
                break
            items.append([_id, value])
        return items

    @staticmethod
    def __dump_cstr(stream, string):
        stream.write(string)
        stream.write('\x00')

    @staticmethod
    def __dump_head(stream, _id, typ):
        stream.write(struct.pack('<BI', typ, _id))

    @staticmethod
    def __dump(stream, _id, typ, value):
        TCPFormat.__dump_head(stream, _id, typ)
        stream.write(value)

    @staticmethod
    def __dump_pack(stream, _id, typ, pack, value):
        TCPFormat.__dump(stream, _id, typ, struct.pack(pack, value))

    @staticmethod
    def __dump_bool(stream, _id, item):
        TCPFormat.__dump_pack(stream, _id, 0, '<B', 1 if item else 0)

    @staticmethod
    def __dump_int(stream, _id, item):
        if item < 0:
            if item < -128:
                typ = (3, '<i')
            else:
                typ = (1, '<b')
        else:
            if item > 127:
                typ = (4, '<I')
            else:
                typ = (2, '<b')
        TCPFormat.__dump_pack(stream, _id, typ[0], typ[1], item)

    @staticmethod
    def __dump_float(stream, _id, item):
        TCPFormat.__dump_pack(stream, _id, 5, '<f', item)

    @staticmethod
    def __dump_str(stream, _id, item):
        TCPFormat.__dump_head(stream, _id, 6)
        TCPFormat.__dump_cstr(stream, item)

    @staticmethod
    def __dump_list(stream, _id, item):
        TCPFormat.__dump_head(stream, _id, 7)
        stream.write(struct.pack('<H', len(item)))
        for val in item:
            stream.write(struct.pack('<I', val))

    @staticmethod
    def __dump_dict(stream, _id, item):
        TCPFormat.__dump_head(stream, _id, 8)
        stream.write(struct.pack('<H', len(item)))
        for key, val in item.items():
            stream.write(struct.pack('<I', val))
            TCPFormat.__dump_cstr(stream, key)
        stream.write(struct.pack('<H', 0))

    @staticmethod
    def dump(items, stream):
        for _id, value in items:
            if type(value) == bool:
                TCPFormat.__dump_bool(stream, _id, value)
            elif type(value) == int:
                TCPFormat.__dump_int(stream, _id, value)
            elif type(value) == float:
                TCPFormat.__dump_float(stream, _id, value)
            elif type(value) == str:
                TCPFormat.__dump_str(stream, _id, value)
            elif type(value) == list:
                TCPFormat.__dump_list(stream, _id, value)
            elif type(value) == dict:
                TCPFormat.__dump_dict(stream, _id, value)


class PipboyFormat(object):
    logger = logging.getLogger("pipboy.PipboyFormat")

    spelling = ['ActiveEffects', 'BodyFlags', 'Caps', 'ClearedStatus', 'Clip',
                'CurrAP', 'CurrCell', 'CurrHP', 'CurrWeight', 'CurrWorldspace',
                'CurrentHPGain', 'Custom', 'DateDay', 'DateMonth', 'DateYear',
                'Description', 'Discovered', 'Doors', 'EffectColor', 'Extents',
                'FavIconType', 'HandleID', 'HeadCondition', 'HeadFlags',
                'Height', 'HolotapePlaying', 'InvComponents', 'Inventory',
                'IsDataUnavailable', 'IsInAnimation', 'IsInAutoVanity',
                'IsInVats', 'IsInVatsPlayback', 'IsLoading', 'IsMenuOpen',
                'IsPipboyNotEquipped', 'IsPlayerDead', 'IsPlayerInDialogue',
                'IsPlayerMovementLocked', 'IsPlayerPipboyLocked',
                'LArmCondition', 'LLegCondition', 'ListVisible', 'Local',
                'LocationFormId', 'LocationMarkerFormId', 'Locations', 'Log',
                'Map', 'MaxAP', 'MaxHP', 'MaxRank', 'MaxWeight',
                'MinigameFormIds', 'Modifier', 'NEX', 'NEY', 'NWX', 'NWY',
                'Name', 'OnDoor', 'PaperdollSection', 'PerkPoints', 'Perks',
                'Player', 'PlayerInfo', 'PlayerName', 'PowerArmor', 'QuestId',
                'Quests', 'RArmCondition', 'RLegCondition', 'RadawayCount',
                'Radio', 'Rank', 'Rotation', 'SWFFile', 'SWX', 'SWY', 'Shared',
                'SlotResists', 'SortMode', 'Special', 'StackID', 'Stats',
                'Status', 'StimpakCount', 'TimeHour', 'TorsoCondition',
                'TotalDamages', 'TotalResists', 'UnderwearType', 'Value',
                'ValueType', 'Version', 'Visible', 'Workshop',
                'WorkshopHappinessPct', 'WorkshopOwned', 'WorkshopPopulation',
                'World', 'X', 'XPLevel', 'XPProgressPct', 'Y', 'canFavorite',
                'damageType', 'diffRating', 'equipState', 'filterFlag',
                'formID', 'inRange', 'isLegendary', 'isPowerArmorItem',
                'itemCardInfoList', 'mapMarkerID', 'radawayObjectID',
                'radawayObjectIDIsValid', 'scaleWithDuration', 'showAsPercent',
                'showIfZero', 'sortedIDS', 'statArray', 'stimpakObjectID',
                'stimpakObjectIDIsValid', 'taggedForSearch', 'workshopData']

    @staticmethod
    def __load_string(stream):
        (length, ) = struct.unpack('<I', stream.read(4))
        return stream.read(length)

    @staticmethod
    def __load_key(stream):
        key = PipboyFormat.__load_string(stream)
        for x in PipboyFormat.spelling:
            if x.lower() == key.lower():
                key = x
                break
        return key

    @staticmethod
    def __load_primitive(stream):
        (typ, ) = struct.unpack('<B', stream.read(1))
        if typ == 0:  # sint32_t
            (value, ) = struct.unpack('<i', stream.read(4))
        elif typ == 1:  # uint32_t
            (value, ) = struct.unpack('<I', stream.read(4))
        elif typ == 2:  # sint64_t
            (value, ) = struct.unpack('<q', stream.read(8))
        elif typ == 3:  # float32_t
            (value, ) = struct.unpack('<f', stream.read(4))
        elif typ == 4:  # float64_t
            (value, ) = struct.unpack('<d', stream.read(8))
        elif typ == 5:  # boolean
            (value, ) = struct.unpack('<B', stream.read(1))
            value = [False, True][value]
        elif typ == 6:  # string
            value = PipboyFormat.__load_string(stream)
        else:
            PipboyFormat.logger.error("Unknown Primitive Typ %d" % typ)
        return value

    @staticmethod
    def __load_array(stream):
        children = []
        (_count, ) = struct.unpack('<I', stream.read(4))
        value = [None] * _count
        for i in range(0, _count):
            (_index, ) = struct.unpack('<I', stream.read(4))
            (_id, child) = PipboyFormat.__load_value(stream)
            value[_index] = _id
            children += child
        return (value, children)

    @staticmethod
    def __load_object(stream):
        children = []
        (_count, ) = struct.unpack('<I', stream.read(4))
        value = {}
        for i in range(0, _count):
            key = PipboyFormat.__load_key(stream)
            (_id, child) = PipboyFormat.__load_value(stream)
            value[key] = _id
            children += child
        return (value, children)

    @staticmethod
    def __load_value(stream):
        (typ, _id) = struct.unpack('<BI', stream.read(5))
        if typ == 0:
            value = PipboyFormat.__load_primitive(stream)
            children = []
        elif typ == 1:
            (value, children) = PipboyFormat.__load_array(stream)
        elif typ == 2:
            (value, children) = PipboyFormat.__load_object(stream)
        else:
            PipboyFormat.logger.error("Unknown Typ %d" % typ)
        children.append([_id, value])
        return (_id, children)

    @staticmethod
    def load(stream):
        (_, result) = PipboyFormat.__load_value(stream)
        return result


class BuiltinFormat(object):
    logger = logging.getLogger("pipboy.BuiltinFormat")

    @staticmethod
    def __load_list(item, _id):
        value = []
        children = []
        next_id = _id + 1
        for subitem in item:
            value.append(next_id)
            (next_id, child) = BuiltinFormat.__load(subitem, next_id)
            children += child
        children.append([_id, value])
        return (next_id, children)

    @staticmethod
    def __load_dict(item, _id):
        value = {}
        children = []
        next_id = _id + 1
        for name, subitem in item.items():
            value[name] = next_id
            (next_id, child) = BuiltinFormat.__load(subitem, next_id)
            children += child
        children.append([_id, value])
        return (next_id, children)

    @staticmethod
    def __load(item, _id):
        if type(item) == dict:
            return BuiltinFormat.__load_dict(item, _id)
        elif type(item) == list:
            return BuiltinFormat.__load_list(item, _id)
        else:
            return (_id + 1, [[_id, item]])

    @staticmethod
    def load(item):
        (_, result) = BuiltinFormat.__load(item, 0)
        return result

    @staticmethod
    def __dump_model(model, _id):
        result = model.get_item(_id)
        if type(result) == list:
            result = [BuiltinFormat.__dump_model(model, v) for v in result]
        elif type(result) == dict:
            result = {k: BuiltinFormat.__dump_model(model, v)
                      for k, v in result.items()}
        return result

    @staticmethod
    def dump_model(model):
        return BuiltinFormat.__dump_model(model, 0)


class Model(object):
    logger = logging.getLogger('pipboy.Model')

    server = {'info': {'lang': 'en',
                       'version': '1.1.30.0'},
              'run_server': False,
              'run_client': False}

    __startup = {
        'Inventory': {},
        "Log": [],
        "Map": {},
        "Perks": [],
        "PlayerInfo": {},
        "Quests": [],
        "Radio": [],
        "Special": [],
        "Stats": {},
        "Status": {
            "EffectColor": [
                0.08, 1.0, 0.09
            ],
            "IsDataUnavailable": True,
            "IsInAnimation": False,
            "IsInAutoVanity": False,
            "IsInVats": False,
            "IsInVatsPlayback": False,
            "IsLoading": False,
            "IsMenuOpen": False,
            "IsPipboyNotEquipped": True,
            "IsPlayerDead": False,
            "IsPlayerInDialogue": False,
            "IsPlayerMovementLocked": False,
            "IsPlayerPipboyLocked": False
        },
        "Workshop": []
    }

    def __clear(self):
        self.__path = {}
        self.__items = {}

    def __init__(self):
        super(Model, self).__init__()
        self.listener = {'update': [], 'command': [], 'map_update': []}
        self.load(BuiltinFormat.load(Model.__startup))

    def register(self, typ, function):
        self.listener[typ].append(function)

    def unregister(self, typ, function):
        if typ not in self.listener:
            self.logger.warn("Could not remove function {func_name} from listener {listener}, listener did not exist.".format(func_name=function.func_name, listener=typ))
            return
        try:
            self.listener[typ].remove(function)
        except ValueError:
            self.logger.warn("Could not remove function {func_name} from listener {listener}, function did not exist.".format(func_name=function.func_name, listener=typ))

    def get_item(self, _id):
        return self.__items.get(_id)

    def get_path(self, _id):
        if _id == 0:
            return "$"
        else:
            (name, parent) = self.__path[_id]
            return self.get_path(parent) + name

    def __get_id(self, _id, path):
        if not path:
            return _id
        match = re.match('^(\.([a-zA-Z0-9]+)|\[([0-9]+)\])(.*)$', path)
        if match:
            item = self.get_item(_id)
            groups = match.groups()
            if groups[1] and type(item) == dict:
                for k, v in item.items():
                    if k.lower() == groups[1].lower():
                        return self.__get_id(v, groups[3])
            elif groups[2] and type(item) == list:
                try:
                    idx = int(groups[2])
                    return self.__get_id(item[idx], groups[3])
                except Exception, e:
                    self.logger.error(str(e))
        return None

    def get_id(self, path):
        if path.startswith('$'):
            return self.__get_id(0, path[1:])
        return None

    def update(self, items):
        changed = []
        for _id, value in items:
            self.__items[_id] = value
            changed.append(_id)
            if type(value) == list:
                for k, v in enumerate(value):
                    self.__path[v] = ("[%d]" % k, _id)
            elif type(value) == dict:
                for k, v in value.items():
                    self.__path[v] = (".%s" % k, _id)
        for func in self.listener['update']:
            func(changed)

    def command(self, _type, args):
        for func in self.listener['command']:
            func(_type, args)

    def map_update(self, data):
        for func in self.listener['map_update']:
            func(data)

    def load(self, items):
        self.__clear()
        self.update(items)

    def dump(self, _id=0, recursive=False):
        item = self.__items[_id]
        result = []
        if recursive:
            if type(item) == list:
                for child in item:
                    result += self.dump(child, recursive)
            elif type(item) == dict:
                for child in item.values():
                    result += self.dump(child, recursive)
        result.append([_id, item])
        return result


class UDPClient(object):
    logger = logging.getLogger('pipboy.UDPClient')

    @staticmethod
    def discover(timeout=5, count=None, busy_allowed=True):
        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, True)
        udp_socket.settimeout(timeout)
        udp_socket.sendto(
            json.dumps({'cmd': 'autodiscover'}), ('<broadcast>', UDP_PORT))
        result = []
        polling = True
        while polling:
            try:
                received, fromaddr = udp_socket.recvfrom(1024)
                ip_addr, port = fromaddr
                try:
                    data = json.loads(received)
                    UDPClient.logger.debug('Discovered {machine_type} at {ip}:{port} ({is_busy})'.format(machine_type=data.get('MachineType'), ip=ip_addr, port=port, is_busy="busy" if data.get('IsBusy') else "free"))
                    if busy_allowed or data.get('IsBusy') == False:
                        data['IpAddr'] = ip_addr
                        data['IpPort'] = port
                        yield (data)  # result.append(data)
                        if count is not None and len(result) >= count:
                            polling = False
                except Exception as e:
                    UDPClient.logger.warn('Unrecognized answer from {ip}:{port}: {data}'.format(data=received, ip=ip_addr, port=port))
            except socket.timeout as e:
                polling = False
        # end while
    # end def discover
# end class


class UDPHandler(SocketServer.DatagramRequestHandler):
    logger = logging.getLogger('pipboy.UDPHandler')
    DISCOVER_MESSAGE = {'IsBusy': False, 'MachineType': 'PC'}

    def handle(self):
        ip_addr, port = self.client_address
        try:
            data = json.load(self.rfile)
        except Exception, e:
            self.logger.error(str(e))
            return
        if data and data.get('cmd') == 'autodiscover':
            json.dump(self.DISCOVER_MESSAGE, self.wfile)
            self.logger.info('Autodiscover from {ip}:{port}'.format(ip=ip_addr, port=port))
        else:
            self.logger.warn('Unrecognized answer from {ip}:{port}: {data}'.format(data=self.rfile.getvalue(), ip=ip_addr, port=port))
    # end def handle
# end class


class UDPServer(SocketServer.ThreadingUDPServer):
    logger = logging.getLogger('pipboy.UDPServer')

    def __init__(self, model):
        self.model = model
        SocketServer.ThreadingUDPServer.__init__(self, ('', UDP_PORT), UDPHandler)


class ServerThread(object):
    logger = logging.getLogger('pipboy.Thread')

    def __init__(self, model, ServerClass):
        self.model = model
        self.server_class = ServerClass

    def start(self):
        self.server = self.server_class(self.model)
        self.thread = threading.Thread(target=self.server.serve_forever,
                                       name=self.server_class.__name__)
        self.thread.daemon = True
        self.thread.start()
        self.logger.debug('%s started' % self.server_class.__name__)

    def stop(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.logger.debug('%s stopped' % self.server_class.__name__)


class TCPHandler:
    logger = logging.getLogger('pipboy.TCPHandler')

    def _old__init__(self, request, client_address, base_server):
        self.request = request
        self.client_address = client_address
        self.base_server = base_server
        self.logger.debug("Created TCPHandler: {r}, {adr}, {server}".format(r=request, adr=client_address, server=base_server))

    def receive(self):
        self.logger.debug("receive")
        header = self.rfile.read(5)
        if len(header) == 0:
            raise Disconnected("receive")
        try:
            size, channel = struct.unpack('<IB', header)
        except Exception as e:
            self.logger.exception("header: '{}'".format(header))
            raise
        data = self.rfile.read(size)
        return (channel, data)

    def send(self, channel, data):
        self.logger.debug("send")
        header = struct.pack('<IB', len(data), channel)
        self.wfile.write(header)
        self.wfile.write(data)

    def __handle_heartbeat(self, data):
        self.logger.debug("handle_heartbeat")
        self.send(0, '')

    def __handle_config(self, data):
        self.logger.debug("handle_config")
        try:
            config = json.loads(data)
            self.logger.info(str(config))
        except Exception, e:
            self.logger.error(str(e))

    def __handle_update(self, data):
        self.logger.debug("handle_update")
        stream = StringIO.StringIO(data)
        self.model.update(TCPFormat.load(stream))

    def __handle_map(self, data):
        self.logger.debug("handle_map")
        self.model.map_update(data)

    def __handle_command(self, data):
        self.logger.debug("handle_command")
        try:
            command = json.loads(data)
            self.model.command(command['type'], command['args'])
        except Exception, e:
            self.logger.error(str(e))

    __handler = {0: __handle_heartbeat,
                 1: __handle_config,
                 3: __handle_update,
                 4: __handle_map,
                 5: __handle_command}

    def handle(self):
        self.logger.debug("handle")
        while self.model.server[self.switch]:
            try:
                (channel, data) = self.receive()
            except Disconnected:
                self.logger.warn("Disconnected. Turned off {}.".format(self.switch))
                self.model.server[self.switch] = False
                self.finish()
                break
            if channel in self.__handler:
                self.__handler[channel](self, data)
            else:
                self.logger.warn("Error Unknown Channel %d : %s" %
                                 (channel, data))

    def send_updates(self, items):
        stream = StringIO.StringIO()
        TCPFormat.dump(items, stream)
        self.send(3, stream.getvalue())

    __command_idx = 1

    def send_command(self, _type, args):
        self.send(5, json.dumps({'type': _type,
                                 'args': args,
                                 'id': self.__command_idx}))
        self.__command_idx += 1


class TCPServerHandler(TCPHandler, SocketServer.StreamRequestHandler):
    logger = logging.getLogger('pipboy.TCPServerHandler')
    switch = 'run_server'

    def listen_update(self, items):
        updates = []
        for item in items:
            updates += self.model.dump(item, False)
        self.send_updates(updates)

    def listen_map_update(self, data):
        self.send(4, data)

    def setup(self):
        self.logger.debug("setup")
        SocketServer.StreamRequestHandler.setup(self)
        self.model = self.server.model
        assert isinstance(self.model, Model)
        self.send(1, json.dumps({'lang': 'en', 'version': '1.1.30.0'}))
        self.send_updates(self.model.dump(0, True))
        self.model.register('update', self.listen_update)
        self.model.register('map_update', self.listen_map_update)

    def finish(self):
        self.logger.debug("finish")
        self.model.unregister('update', self.listen_update)
        SocketServer.StreamRequestHandler.finish(self)


class TCPServer(SocketServer.ThreadingTCPServer):
    def __init__(self, model):
        self.model = model
        SocketServer.ThreadingTCPServer.__init__(self, ('', TCP_PORT), TCPServerHandler)

    def server_activate(self):
        self.model.server['run_server'] = True
        SocketServer.ThreadingTCPServer.server_activate(self)

    def shutdown(self):
        self.model.server['run_server'] = False
        SocketServer.ThreadingTCPServer.shutdown(self)


class TCPClientHandler(TCPHandler, SocketServer.StreamRequestHandler):
    logger = logging.getLogger('pipboy.TCPClientHandler')
    switch = 'run_client'

    def heartbeat(self):
        while self.model.server[self.switch]:
            self.logger.debug("heartbeat")
            self.send(0, '')
            time.sleep(1)

    def listen_command(self, _type, args):
        self.send_command(_type, args)

    def setup(self):
        self.logger.debug("setup")
        SocketServer.StreamRequestHandler.setup(self)
        self.model = self.server.model
        self.model.register('command', self.listen_command)
        thread = threading.Thread(target=self.heartbeat, name="Heartbeat")
        thread.start()

    def finish(self):
        self.logger.debug("finish")
        self.hb = False
        self.model.unregister('command', self.listen_command)
        SocketServer.StreamRequestHandler.finish(self)


class TCPClient(object):
    logger = logging.getLogger('pipboy.TCPClient')

    def connect(self, server, model):
        self.model = model
        self.server = server
        self.thread = threading.Thread(target=self.run, name=self.__class__.__name__)
        self.thread.daemon = True
        self.thread.start()
        self.logger.info('{} started'.format(self.__class__.__name__))

    def run(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((self.server, TCP_PORT))
        self.model.server['run_client'] = True
        TCPClientHandler(self.socket, (self.server, TCP_PORT), self)

    def disconnect(self):
        self.model.server['run_client'] = False
        self.socket.close()


class View(object):
    logger = logging.getLogger('pipboy.Console')

    ignore = ['$.PlayerInfo.TimeHour', '$.Map.Local.Player.X',
              '$.Map.Local.Player.Y', '$.Map.Local.Player.Rotation',
              '$.Map.World.Player.X', '$.Map.World.Player.Y',
              '$.Map.World.Player.Rotation']

    def __init__(self, model):
        self.model = model
        model.register('update', self.listen_update)
        model.register('command', self.listen_command)
        model.register('map_update', self.listen_map_update)

    def listen_update(self, items):
        """
        This listens and prints all new data, excluding those in the `ignore` list.
        :param items: list of items
        :return:
        """
        for item in items:
            assert isinstance(item, Model)
            path = self.model.get_path(item)
            ig = False
            for i in self.ignore:
                if i.lower() == path.lower():
                    ig = True
            if not ig:
                item = self.model.get_item(item)
                self.print_update(path, item)

    def listen_command(self, _type, args):
        """
        This is called when a command is issued.
        :param _type:
        :param args:
        :return:
        """
        print("{type} {args}".format(type=_type, args=args))

    def listen_map_update(self, data):
        """
        This function receives the data for the local map.
        :param data: the data
        """
        pass

    # noinspection PyMethodMayBeStatic
    def print_update(self, path, item):
        print("{path} {value}".format(path, item))


class Console(cmd.Cmd):
    logger = logging.getLogger('pipboy.Console')

    def __init__(self):
        cmd.Cmd.__init__(self)
        logging.basicConfig(level=logging.INFO)
        self.prompt = 'PipBoy: '
        self.model = Model()
        self.view = View(self.model)
        readline.set_completer_delims(readline.get_completer_delims(
        ).translate(None, '$[]'))

    def emptyline(self):
        pass

    def do_EOF(self, line):
        return True

    def complete_loglevel(self, text, line, begidx, endidx):
        return [i
                for i in logging._levelNames
                if type(i) == str and i.startswith(text)]

    def do_loglevel(self, line):
        """
        `loglevel <level>` - sets a logging level. Choose 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'.
        """
        try:
            logging.getLogger().setLevel(line)
        except Exception, e:
            self.logger.error(e)

    __discover = None

    def do_discover(self, line):
        """
        `discover` - does the udp discover and shows the responding games
        """
        self.__discover = UDPClient.discover()  # caches for completion
        for server in self.__discover:
            print server

    def complete_connect(self, text, line, begidx, endidx):
        if not self.__discover:
            self.__discover = UDPClient.discover(timeout=2, busy_allowed=False)
        return [
            server['IpAddr']
                for server in self.__discover if
                    server['IsBusy'] == False and server['IpAddr'].startswith(text)
                    # checking 'IsBusy' again because cached version might include busy ones.
            ]

    def do_connect(self, line):
        """
        `connect <gameip>` - connects to the specfied game
        """
        self.client = TCPClient()
        self.client.connect(line, self.model)
        print "Connect - %s" % line

    def do_disconnect(self, line):
        """
        `disconnect` - disconnects from game
        """
        if hasattr(self, "client") and self.client:
            self.client.disconnect()
        else:
            self.logger.warn("Not connected.")
        print("Disconnect - %s" % line)

    def do_autoconnect(self, line):
        """
        Connects to the first available game.
        """
        if not self.__discover:
            self.__discover = UDPClient.discover(timeout=2,
                                                 count=1,
                                                 busy_allowed=False)
        print "Connect - %s" % line

    def __complete_path(self, text):
        if not text:
            return ['$']
        else:
            _id = self.model.get_id(text)
            self.logger.debug(str(_id))
            if _id == None:
                tmp = re.split('(\.|\[)[^.[]*$', text)
                _id = self.model.get_id(tmp[0])
            if _id != None:
                item = self.model.get_item(_id)
                if item:
                    children = None
                    if type(item) == list:
                        children = item
                    elif type(item) == dict:
                        children = item.values()
                    if children:
                        result = []
                        for child in children:
                            child_path = self.model.get_path(child)
                            if child_path and child_path.lower().startswith(
                                    text.lower()):
                                result.append(child_path)
                        return result
        return None

    def complete_get(self, text, line, begidx, endidx):
        return self.__complete_path(text)

    def do_get(self, line):
        """
        `get <path>` - gets the value at path from the database (e.g. get $.PlayerInfo.PlayerName) (complete with Tab)
        """
        for path in re.split('\s+', line.strip()):
            _id = self.model.get_id(path)
            if type(_id) == int:
                print "0x%x - %s" % (_id, str(self.model.get_item(_id)))
            else:
                print "Path not found - %s" % path

    def complete_set(self, text, line, begidx, endidx):
        return self.__complete_path(text)

    def do_set(self, line):
        """
        `set <path> <value>` - sets the value at path from the database (e.g. get $.PlayerInfo.PlayerName) (complete with Tab)
        """
        args = line.split(' ', 1)
        _id = self.model.get_id(args[0])
        if type(_id) == int:
            value = args[1].strip()
            try:
                value = json.loads(value)
            except Exception, e:
                self.logger.debug(str(e))
            item = self.model.get_item(_id)
            if type(item) != type(value):
                print "Type mismatch must be %s" % type(item)
            else:
                self.model.update([[_id, value]])
        else:
            print "Path not found"

    def do_load(self, line):
        """
        `load <file>` loads a file in the format of Channel 3
        """
        with open(line, 'rb') as stream:
            try:
                self.model.load(TCPFormat.load(stream))
            except Exception, e:
                self.logger.error(e)
                print("Not in TCPFormat - {}".format(line))

    def do_save(self, line):
        """
        `save <file>` - saves database to file in the format of Channel 3
        """
        with open(line, 'wb') as stream:
            TCPFormat.dump(self.model.dump(0, True), stream)

    def do_savejson(self, line):
        """
        `savejson <file>` - saves database to JSON-file
        """
        with open(line, 'wb') as stream:
            json.dump(
                BuiltinFormat.dump_model(self.model),
                stream,
                indent=4,
                sort_keys=True)

    def do_loadapp(self, line):
        """
        `loadapp <file>` loads a file in the format found in apk (DemoMode.bin)
        """
        try:
            with open(line, 'rb') as stream:
                try:
                    self.model.load(PipboyFormat.load(stream))
                except Exception, e:
                    self.logger.error(e)
                    print("Not in PipboyFormat - {}".format(line))
        except IOError as e:
            self.logger.warn("{}".format(e))


    def do_start(self, line):
        """
        `start` - starts server so app can connect
        """
        if not hasattr(self, "tcp_server") or self.tcp_server is None:
            self.tcp_server = ServerThread(self.model, TCPServer)
            self.tcp_server.start()
        else:
            self.logger.warn("TCP server already running.")
        if not hasattr(self, "udp_server") or self.udp_server is None:
            self.udp_server = ServerThread(self.model, UDPServer)
            self.udp_server.start()
        else:
            self.logger.warn("UDP server already running.")
        #end if


    def do_stop(self, line):
        """
        `stop` - stops server
        """
        self.logger.debug("Stop requested.")
        if hasattr(self, "udp_server") and self.udp_server:
            self.udp_server.stop()
            self.udp_server = None
            self.logger.debug("Stopped UDP.")
        else:
            self.logger.info("UDP already stopped.")
        if hasattr(self, "tcp_server") and self.tcp_server:
            self.tcp_server.stop()
            self.tcp_server = None
            self.logger.debug("Stopped TCP.")
        else:
            self.logger.info("TCP already stopped.")


    def do_threads(self, line):
        """
        `threads` - show running threads
        """
        for th in threading.enumerate():
            print th

    def do_rawcmd(self, line):
        """
        `rawcmd <type> <args>` - sends a command to game (testing only)
        """
        args = line.split(' ', 1)
        try:
            command = int(args[0])
            value = args[1].strip()
            value = json.loads(value)
            print command, value
            self.model.command(command, value)
        except Exception, e:
            self.logger.error(str(e))


class Disconnected(Exception):
    pass

if __name__ == '__main__':
    Console().cmdloop()
