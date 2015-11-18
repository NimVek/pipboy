# Pip-Boy

This little pice of code should emulate the app, server or should be used as MitM-Proxy for the Bethesda Fallout 4 PipBoy Companion App Protocol.
After some investigation on the communication between the app and the game, i wrote a python script das emulates the client or the server.
But to use it for MitM it must be rewritten so currently only the client part works. But server would be fine soon.

## Usage

To run this little script only a working python interpreter is needed.

### Client

Simply run `client.py` it has a `cmd.Cmd` based interpreter.

| Command | Description |
|---|---|
| `discover` | does the udp discover and shows the responding games |
| `connect <game>` | connects to the specfied game |
| `autoconnect` | does discover and connects to the first responding game |

## Known Bugs

Please remark this is still in development, so no checking of consistency is down, whether on user input nor on network input.
I've investigated only the Android-App <-> PC Game Connection, maybe it works with other combination, maybe not.
Feel free to try and help me to make it better.
Maybe you can provide me some input simply run `tcpdump -s 0 -w dump host <ip of handheld>` or `tcpdump -s 0 -w dump port 27000 or port 28000`
