#!/usr/bin/env python

import io
import json
import logging
import socket
import socketserver
import struct
import threading
import time

from .format import TCPFormat
from .mvc import Model


TCP_PORT = 27000


class Disconnected(Exception):
    pass


class TCPHandler:
    logger = logging.getLogger("pipboy.TCPHandler")

    def _old__init__(self, request, client_address, base_server):
        self.request = request
        self.client_address = client_address
        self.base_server = base_server
        self.logger.debug(
            "Created TCPHandler: {r}, {adr}, {server}".format(
                r=request, adr=client_address, server=base_server
            )
        )

    def receive(self):
        self.logger.debug("receive")
        header = self.rfile.read(5)
        if len(header) == 0:
            raise Disconnected("receive")
        try:
            size, channel = struct.unpack("<IB", header)
        except Exception:
            self.logger.exception("header: '{}'".format(header))
            raise
        data = self.rfile.read(size)
        return (channel, data)

    def send(self, channel, data):
        self.logger.debug("send {channel}: {data}".format(channel=channel, data=data))
        header = struct.pack("<IB", len(data), channel)
        self.wfile.write(header)
        self.wfile.write(data)

    def __handle_heartbeat(self, data):
        self.logger.debug("handle_heartbeat")
        self.send(0, b"")

    def __handle_config(self, data):
        self.logger.debug("handle_config")
        try:
            config = json.loads(data.decode())
            self.logger.info(str(config))
        except Exception as e:
            self.logger.error(str(e))

    def __handle_update(self, data):
        self.logger.debug("handle_update")
        stream = io.BytesIO(data)
        self.model.update(TCPFormat.load(stream))

    def __handle_map(self, data):
        self.logger.debug("handle_map")
        self.model.map_update(data)

    def __handle_command(self, data):
        self.logger.debug("handle_command")
        try:
            command = json.loads(data.decode())
            self.model.command(command["type"], command["args"])
        except Exception as e:
            self.logger.error(str(e))

    __handler = {
        0: __handle_heartbeat,
        1: __handle_config,
        3: __handle_update,
        4: __handle_map,
        5: __handle_command,
    }

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
                self.logger.warn("Error Unknown Channel %d : %s" % (channel, data))

    def send_updates(self, items):
        stream = io.BytesIO()
        TCPFormat.dump(items, stream)
        self.send(3, stream.getvalue())

    __command_idx = 1

    def send_command(self, _type, args):
        self.send(
            5,
            json.dumps(
                {"type": _type, "args": args, "id": self.__command_idx}
            ).encode(),
        )
        self.__command_idx += 1


class TCPServerHandler(TCPHandler, socketserver.StreamRequestHandler):
    logger = logging.getLogger("pipboy.TCPServerHandler")
    switch = "run_server"

    def listen_update(self, items):
        updates = []
        for item in items:
            updates += self.model.dump(item, False)
        self.send_updates(updates)

    def listen_map_update(self, data):
        self.send(4, data)

    def setup(self):
        self.logger.debug("setup")
        socketserver.StreamRequestHandler.setup(self)
        self.model = self.server.model
        assert isinstance(self.model, Model)
        self.send(1, json.dumps({"lang": "en", "version": "1.1.30.0"}).encode())
        self.send_updates(self.model.dump(0, True))
        self.model.register("update", self.listen_update)
        self.model.register("map_update", self.listen_map_update)

    def finish(self):
        self.logger.debug("finish")
        self.model.unregister("update", self.listen_update)
        socketserver.StreamRequestHandler.finish(self)


class TCPServer(socketserver.ThreadingTCPServer):
    def __init__(self, model):
        self.model = model
        socketserver.ThreadingTCPServer.__init__(self, ("", TCP_PORT), TCPServerHandler)

    def server_activate(self):
        self.model.server["run_server"] = True
        socketserver.ThreadingTCPServer.server_activate(self)

    def shutdown(self):
        self.model.server["run_server"] = False
        socketserver.ThreadingTCPServer.shutdown(self)


class TCPClientHandler(TCPHandler, socketserver.StreamRequestHandler):
    logger = logging.getLogger("pipboy.TCPClientHandler")
    switch = "run_client"

    def heartbeat(self):
        while self.model.server[self.switch]:
            self.logger.debug("heartbeat")
            self.send(0, b"")
            time.sleep(1)

    def listen_command(self, _type, args):
        self.send_command(_type, args)

    def setup(self):
        self.logger.debug("setup")
        socketserver.StreamRequestHandler.setup(self)
        self.model = self.server.model
        self.model.register("command", self.listen_command)
        thread = threading.Thread(target=self.heartbeat, name="Heartbeat")
        thread.start()

    def finish(self):
        self.logger.debug("finish")
        self.hb = False
        self.model.unregister("command", self.listen_command)
        socketserver.StreamRequestHandler.finish(self)


class TCPClient(object):
    logger = logging.getLogger("pipboy.TCPClient")

    def connect(self, server, model):
        self.model = model
        self.server = server
        self.thread = threading.Thread(target=self.run, name=self.__class__.__name__)
        self.thread.daemon = True
        self.thread.start()
        self.logger.info("{} started".format(self.__class__.__name__))

    def run(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((self.server, TCP_PORT))
        self.model.server["run_client"] = True
        TCPClientHandler(self.socket, (self.server, TCP_PORT), self)

    def disconnect(self):
        self.model.server["run_client"] = False
        self.socket.close()
