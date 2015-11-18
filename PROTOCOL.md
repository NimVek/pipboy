## Discover

### PC & PS4

The app send following broadcast packet to **UDP/28000**
```json
{"cmd": "autodiscover"}
```
It send receives a packet containing Information about the game.
The machine type is either `PC` or `PS4`.
```json
{"IsBusy": false, "MachineType": "PC"}
```

### XBox One

The app sends a 16 byte broadcast packet to port **UDP/5050**
The content is omitted because of possible privacy issues. (Can anyone explain me the protocol? Its XBox standard.)

## Communication

On PC and PS4 the App connects to the Game ob Port **TCP/27000**
All data of the communication ist little-endian.
The resulting stream can be separated in individual packets of following style.
```C
struct Packet {
  uint32_t size,
  uint8_t channel,
  uint8_t content[size]
}
```

### Channel 0

Seems to be for keep alive only.
The size of the packets are always *zero*, so no additional information are served.

### Channel 1

On connect the first and only packet the Game sends contains some additional Info about the game.

```JSON
{"lang": "de", "version": "1.1.30.0"}
```

### Channel 3

This channel contains binary data the second packet of the server contains the whole database.
Future packets do only updates to database.
The database ist is a array of items while lists or dicts reference to the indexes of the array.

```C
struct Entry {
  uint8_t type,
  uint32_t id,
  switch (type) {
    case 0:
      uint8_t boolean,
      break;
    case 1:
      sint8_t integer,
      break;
    case 2:
      uint8_t integer,
      break;
    case 3:
      sint32_t integer,
      break;
    case 4:
      uint32_t integer,
      break;
    case 5:
      float32_t floating_point,
      break;
    case 6:
      char_t *string, // zero-terminated
      break;
    case 7: // list
      uint16_t count,
      uint32_t references[count]
      break;
    case 8:
      uint16_t count,
      DictEntry[count],
      uint16_t dummy, // is always zero
      break;
  }
}

struct DictEntry {
      uint32_t reference,
      char_t *name // zero-terminated
}
```
#### Example Database

Following JSON

```JSON
{ "foo" : 
  { "bar": "baz",
    "list": [ "one", "two", 3 ]
  }
}
```

will result in this database

| Index  |  Value | 
|---|---|
| 0 | { "foo": 1 } |
| 1 | { "bar": 2, "list": 3 } |
| 2 | "baz" |
| 3 | [ 4, 5, 6 ] |
| 4 | "one" |
| 5 | "two" |
| 6 | 3 |

### Channel 5

The app send commands to the game over this channel.
The type is seen in range of 0 to 14, the args differ on type and the id increments with every command send.
```JSON
{"type": 14, "args": [], "id": 6}
```
