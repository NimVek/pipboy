# Pip-Boy

This little pice of code should emulate the app, server or run as MitM-Proxy for the Bethesda Fallout 4 PipBoy Companion App Protocol.
This script is based on some investigation of the communcation between tha app and the game.
You can use it standalone, with the app, then running as proxy, or as a server for the app.

## Usage

To run this little script only a working python interpreter is needed.

Simply run `pipboy.py` it has a `cmd.Cmd` based interpreter.

| Command | Description |
|---|---|
| `discover` | does the udp discover and shows the responding games |
| `connect <gameip>` | connects to the specfied game |
| `autoconnect` | connects to the first available game |
| `disconnect` | disconnects from game |
| `get <path>` | gets the value at path from the database (e.g. get $.PlayerInfo.PlayerName) (complete with Tab)  |
| `set <path> <value>` | sets the value  |
| `load <file>` | loads a file in the format of Channel 3  |
| `loadapp <file>` | loads a file in the format found in apk (DemoMode.bin)  |
| `loglevel <level>` | Python logger levels, see [(list of levels)](https://docs.python.org/2/library/logging.html#logging-levels) |
| `updates <1/0>` | If database updates should be printed. |
| `save <file>` | saves database to file in the format of Channel 3  |
| `savejson <file>` | saves database to JSON-file |
| `start` | starts server so app can connect |
| `stop` | stops server |
| `threads` | show running threads |
| `rawcmd <type> <args>` | sends a command to game (testing only) |

## Known Bugs

Thanks to @luckydonald for finding and fixing ;)

* does not check for closed connection

Please remark this is still in development, so no checking of consistency is done, whether on user input nor on network input.
I've investigated only the Android-App <-> PC Game Connection, maybe it works with other combination, maybe not.
Feel free to try and help me to make it better.
I like to have some communication dumps of XBox Users. Hard to describe what i need, discover is over UDP/5050.
Maybe the XBOX has TCP/27000 open like PC/PS4.
Maybe you can provide me some input simply run `tcpdump -s 0 -w dump host <ip of handheld>` or `tcpdump -s 0 -w dump port 27000 or port 28000`
