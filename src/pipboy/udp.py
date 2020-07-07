#!/usr/bin/env python

import json
import logging
import socket
import socketserver


UDP_PORT = 28000


class UDPClient(object):
    logger = logging.getLogger("pipboy.UDPClient")

    @staticmethod
    def discover(timeout=5, count=None, busy_allowed=True):
        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, True)
        udp_socket.settimeout(timeout)
        udp_socket.sendto(
            json.dumps({"cmd": "autodiscover"}), ("<broadcast>", UDP_PORT)
        )
        result = []
        polling = True
        while polling:
            try:
                received, fromaddr = udp_socket.recvfrom(1024)
                ip_addr, port = fromaddr
                try:
                    data = json.loads(received)
                    UDPClient.logger.debug(
                        "Discovered {machine_type} at {ip}:{port} ({is_busy})".format(
                            machine_type=data.get("MachineType"),
                            ip=ip_addr,
                            port=port,
                            is_busy="busy" if data.get("IsBusy") else "free",
                        )
                    )
                    if busy_allowed or data.get("IsBusy") is False:
                        data["IpAddr"] = ip_addr
                        data["IpPort"] = port
                        yield (data)  # result.append(data)
                        if count is not None and len(result) >= count:
                            polling = False
                except Exception:
                    UDPClient.logger.warn(
                        "Unrecognized answer from {ip}:{port}: {data}".format(
                            data=received, ip=ip_addr, port=port
                        )
                    )
            except socket.timeout:
                polling = False
        # end while

    # end def discover


# end class


class UDPHandler(socketserver.DatagramRequestHandler):
    logger = logging.getLogger("pipboy.UDPHandler")
    DISCOVER_MESSAGE = {"IsBusy": False, "MachineType": "PC"}

    def handle(self):
        ip_addr, port = self.client_address
        try:
            data = json.load(self.rfile)
        except Exception as e:
            self.logger.error(str(e))
            return
        if data and data.get("cmd") == "autodiscover":
            json.dump(self.DISCOVER_MESSAGE, self.wfile)
            self.logger.info(
                "Autodiscover from {ip}:{port}".format(ip=ip_addr, port=port)
            )
        else:
            self.logger.warn(
                "Unrecognized answer from {ip}:{port}: {data}".format(
                    data=self.rfile.getvalue(), ip=ip_addr, port=port
                )
            )

    # end def handle


# end class


class UDPServer(socketserver.ThreadingUDPServer):
    logger = logging.getLogger("pipboy.UDPServer")

    def __init__(self, model):
        self.model = model
        socketserver.ThreadingUDPServer.__init__(self, ("", UDP_PORT), UDPHandler)
