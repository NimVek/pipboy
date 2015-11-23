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

### Channel 0 (Heartbeat)

Seems to be for keep alive only.
The size of the packets are always *zero*, so no additional information are served.

### Channel 1

On connect the first and only packet the Game sends contains some additional Info about the game.

```JSON
{"lang": "de", "version": "1.1.30.0"}
```

### Channel 3 (Database Update)

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

### Channel 4 (Local Map Update)

The game sends binary imagedata wich is displayed if you choose local map on your app.
Its seems to be rendered each time so maybe, we are able to detect movement? Lets see in future ;)

```C
struct Extend {
  float32_t x,
  float32_t y
}

struct Map {
      uint32_t width,
      uint32_t height,
      Extend nw,
      Extend ne,
      Extend sw,
      uint8_t pixel[ width * height ]
}
```

### Channel 5 (Command Request)

The app send commands to the game over this channel.
The type is seen in range of 0 to 14, the args differ on type and the id increments with every command send.
```JSON
{"type": 1, "args": [4207600675, 7, 494, [0, 1]], "id": 3}
```

|  Type  |  Args  | Comment  |
|---|---|---|
|  0  |  `[ <handleId>, 0, <$.Inventory.Version> ]`  | Use an instance of item specified by `<handleId>`  |
|  1  |  `[ <handleId>, <count>, <$.Inventory.Version>, <additional> ]`  | Drop `<count>` instances of item, for single item `<additional> = [0]`, else `<additional> = [0,1]`  |
|  2  |  `[<handleId>, [0], <position>, <$.Inventory.Version>]` | Put item on favorite `<position>` counts from far left 0 to right 5, and north 6 to south 11  |
|  3  |  `[<componentFormId>, <$.Inventory.Version>]` | Toggle *Tag for search* on component specified by `<componentFormId>`  |
|  4  |  `[<page>]` | Cycle through search mode on inventory page ( 0: Weapons, 1: Apparel, 2: Aid, 3: Misc, 4: Junk, 5: Mods, 6: Ammo )  |
|  5  |  `[<QuestId>, ??, ??]` | Toggle marker for quest |
|  6  |  `[ <x>, <y>, false ]` | Place custom marker at `<x>,<y>` |
|  7  |  `[]`  | remove custom marker  |
|  8  |   |   |
|  9  |  `[<id>]` | Fast travel to location with index `<id>` in database  |
|  10  |   |   |
|  11  |   |   |
|  12  |  `[<id>]`  |  Toggle radio with index `<id>` in database   |
|  13  |  `[]`   |  Toggle receiving of local map update   |
|  14  |  `[]`   |  Refresh?? Command with no result   |

### Channel 6 (Command Response)

Is a response channel for commands sends by app, only seen for command type `6`

```JSON
{"allowed":true,"id":3,"success":true}
```
