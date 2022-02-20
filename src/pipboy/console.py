#!/usr/bin/env python

import cmd
import json
import logging
import re
import readline
import threading

from typing import Optional

from .format import BuiltinFormat, PipboyFormat, TCPFormat
from .mvc import Model, View
from .tcp import TCPClient, TCPServer
from .udp import UDPClient, UDPServer


class ServerThread(object):
    logger = logging.getLogger("pipboy.Thread")

    def __init__(self, model, ServerClass):
        self.model = model
        self.server_class = ServerClass

    def start(self):
        self.server = self.server_class(self.model)
        self.thread = threading.Thread(
            target=self.server.serve_forever, name=self.server_class.__name__
        )
        self.thread.daemon = True
        self.thread.start()
        self.logger.debug("%s started" % self.server_class.__name__)

    def stop(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.logger.debug("%s stopped" % self.server_class.__name__)


class Console(cmd.Cmd):
    logger = logging.getLogger("pipboy.Console")

    def __init__(self):
        cmd.Cmd.__init__(self)
        logging.basicConfig(level=logging.INFO)
        self.prompt = "PipBoy: "
        self.model = Model()
        self.view = View(self.model)
        self.client = None
        readline.set_completer_delims(
            readline.get_completer_delims().translate(str.maketrans("", "", "$[]"))
        )
        self.tcp_server: Optional[ServerThread] = None
        self.udp_server: Optional[ServerThread] = None

    def emptyline(self):
        pass

    def do_EOF(self, line):
        return True

    def complete_loglevel(self, text, line, begidx, endidx):
        return [i for i in logging._nameToLevel if i.startswith(text)]

    def do_loglevel(self, line):
        """
        `loglevel <level>` - sets a logging level. Choose 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'.
        """
        try:
            logging.getLogger().setLevel(line)
        except Exception as e:
            self.logger.error(e)

    def do_updates(self, line):
        """
        `updates <1/0>` - If database updates should be printed.
        :param line:
        :return:
        """
        if line.strip().lower() in ["1", "y", "yes", "true"]:
            self.view.should_spam = True
            print("Turned output on.")
        else:
            self.view.should_spam = False
            print("Turned output off.")

    __discover = None
    # List of Fallout apps. Can be busy.

    def do_discover(self, line):
        """
        `discover` - does the udp discover and shows the responding games
        """
        discover = []  # caches for completion
        for server in UDPClient.discover():
            print(
                (
                    "{ip} ({type}, {is_busy})".format(
                        ip=server["IpAddr"],
                        type=server["MachineType"],
                        is_busy="busy" if server["IsBusy"] else "free",
                    )
                )
            )
            discover.append(server)
        self.__discover = discover

    def complete_connect(self, text, line, begidx, endidx):
        if not self.__discover:
            self.__discover = list(UDPClient.discover(timeout=2))
        return [
            server["IpAddr"]
            for server in self.__discover
            if server["IsBusy"] is False and server["IpAddr"].startswith(text)
            # checking 'IsBusy' again because cached version might include busy ones.
        ]

    def do_connect(self, line):
        """
        `connect <gameip>` - connects to the specfied game
        """
        if len(line.strip()) == 0:
            print("Please provide an IP")
            return
        print(("Connecting to {line}".format(line=line)))
        if not hasattr(self, "client") or not self.client:
            self.client = TCPClient()
        else:
            self.logger.warn("Already Connected. Disconnecting previous session.")
            self.client.disconnect()
        try:
            self.client.connect(line, self.model)
        except Exception as e:
            self.logger.error("Could not connect: {err}".format(err=str(e)))
        else:
            print("Connected.")

    def do_disconnect(self, line):
        """
        `disconnect` - disconnects from game
        """
        if hasattr(self, "client") and self.client:
            self.client.disconnect()
        else:
            self.logger.warn("Not connected.")
        print(("Disconnect - %s" % line))

    def do_autoconnect(self, line):
        """
        `autoconnect` - Connects to the first available game.
        """
        discover = self.__discover
        if not discover:
            discover = list(UDPClient.discover(timeout=2, count=1, busy_allowed=False))
        if not hasattr(self, "client") or not self.client:
            self.client = TCPClient()
            self.logger.debug("created client")
        ip = discover[0]["IpAddr"]
        self.client.connect(ip, self.model)
        print(("Connect - {ip}".format(ip=ip)))

    def __complete_path(self, text):
        if not text:
            return ["$"]
        else:
            _id = self.model.get_id(text)
            self.logger.debug(str(_id))
            if _id is None:
                tmp = re.split(r"(\.|\[)[^.[]*$", text)
                _id = self.model.get_id(tmp[0])
            if _id is not None:
                item = self.model.get_item(_id)
                if item:
                    children = None
                    if type(item) == list:
                        children = item
                    elif type(item) == dict:
                        children = list(item.values())
                    if children:
                        result = []
                        for child in children:
                            child_path = self.model.get_path(child)
                            if child_path and child_path.lower().startswith(
                                text.lower()
                            ):
                                result.append(child_path)
                        return result
        return None

    def complete_get(self, text, line, begidx, endidx):
        return self.__complete_path(text)

    def do_get(self, line):
        """
        `get <path>` - gets the value at path from the database (e.g. get $.PlayerInfo.PlayerName) (complete with Tab)
        """
        for path in re.split(r"\s+", line.strip()):
            _id = self.model.get_id(path)
            if type(_id) == int:
                print("0x%x - %s" % (_id, str(self.model.get_item(_id))))
            else:
                print("Path not found - %s" % path)

    def complete_set(self, text, line, begidx, endidx):
        return self.__complete_path(text)

    def do_set(self, line):
        """
        `set <path> <value>` - sets the value at path from the database (e.g. get $.PlayerInfo.PlayerName) (complete with Tab)
        """
        args = line.split(" ", 1)
        _id = self.model.get_id(args[0])
        if type(_id) == int:
            value = args[1].strip()
            try:
                value = json.loads(value)
            except Exception as e:
                self.logger.debug(str(e))
            item = self.model.get_item(_id)
            if type(item) != type(value):
                print("Type mismatch must be %s" % type(item))
            else:
                self.model.update([[_id, value]])
        else:
            print("Path not found")

    def do_load(self, line):
        """
        `load <file>` loads a file in the format of Channel 3
        """
        with open(line, "rb") as stream:
            try:
                self.model.load(TCPFormat.load(stream))
            except Exception as e:
                self.logger.error(e)
                print(("Not in TCPFormat - {}".format(line)))

    def do_save(self, line):
        """
        `save <file>` - saves database to file in the format of Channel 3
        """
        with open(line, "wb") as stream:
            TCPFormat.dump(self.model.dump(0, True), stream)

    def do_savejson(self, line):
        """
        `savejson <file>` - saves database to JSON-file
        """
        with open(line, "w") as stream:
            json.dump(
                BuiltinFormat.dump_model(self.model), stream, indent=4, sort_keys=True
            )

    def do_loadapp(self, line):
        """
        `loadapp <file>` loads a file in the format found in apk (DemoMode.bin)
        """
        try:
            with open(line, "rb") as stream:
                try:
                    self.model.load(PipboyFormat.load(stream))
                except Exception as e:
                    self.logger.error(e)
                    print(("Not in PipboyFormat - {}".format(line)))
        except IOError as e:
            self.logger.warn("{}".format(e))

    def do_start(self, line):
        """
        `start` - starts server so app can connect
        """
        if self.tcp_server is None:
            self.tcp_server = ServerThread(self.model, TCPServer)
            self.tcp_server.start()
        else:
            self.logger.warn("TCP server already running.")
        if self.udp_server is None:
            self.udp_server = ServerThread(self.model, UDPServer)
            self.udp_server.start()
        else:
            self.logger.warn("UDP server already running.")
        # end if

    def do_stop(self, line):
        """
        `stop` - stops server
        """
        self.logger.debug("Stop requested.")
        if self.udp_server:
            self.udp_server.stop()
            self.udp_server = None
            self.logger.debug("Stopped UDP.")
        else:
            self.logger.info("UDP already stopped.")
        if self.tcp_server:
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
            print(th)

    def do_rawcmd(self, line):
        """
        `rawcmd <type> <args>` - sends a command to game (testing only)
        """
        args = line.split(" ", 1)
        try:
            command = int(args[0])
            value = args[1].strip()
            value = json.loads(value)
            print(command, value)
            self.model.command(command, value)
        except Exception as e:
            self.logger.error(str(e))
