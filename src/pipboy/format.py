#!/usr/bin/env python

import logging
import struct


class TCPFormat(object):
    logger = logging.getLogger("pipboy.TCPFormat")

    @staticmethod
    def __load_bool(stream):
        (val,) = struct.unpack("<B", stream.read(1))
        val = [False, True][val]
        return val

    @staticmethod
    def __load_native(stream, size, unpack):
        (val,) = struct.unpack(unpack, stream.read(size))
        return val

    @staticmethod
    def __load_cstr(stream):
        buffer = bytearray()
        while True:
            byte = stream.read(1)
            if byte == b"\x00":
                return buffer.decode()
            else:
                buffer += byte

    @staticmethod
    def __load_list(stream):
        value = []
        (_count,) = struct.unpack("<H", stream.read(2))
        for _i in range(0, _count):
            (tmp,) = struct.unpack("<I", stream.read(4))
            value.append(tmp)
        return value

    @staticmethod
    def __load_dict(stream):
        value = {}
        (_count,) = struct.unpack("<H", stream.read(2))
        for _i in range(0, _count):
            (ref,) = struct.unpack("<I", stream.read(4))
            attribute = TCPFormat.__load_cstr(stream)
            value[attribute] = ref
        (_count,) = struct.unpack("<H", stream.read(2))
        for _i in range(0, _count):
            (ref,) = struct.unpack("<I", stream.read(4))
        return value

    @staticmethod
    def load(stream):
        items = []
        while True:
            typ = stream.read(1)
            if not typ:
                break
            (typ,) = struct.unpack("<B", typ)
            (_id,) = struct.unpack("<I", stream.read(4))
            if typ == 0:  # confirmed bool
                value = TCPFormat.__load_bool(stream)
            elif typ == 1:
                value = TCPFormat.__load_native(stream, 1, "<b")
            elif typ == 2:
                value = TCPFormat.__load_native(stream, 1, "<B")
            elif typ == 3:
                value = TCPFormat.__load_native(stream, 4, "<i")
            elif typ == 4:  # confirmed uint_32
                value = TCPFormat.__load_native(stream, 4, "<I")
            elif typ == 5:  # confirmed float
                value = TCPFormat.__load_native(stream, 4, "<f")
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
        stream.write(string.encode())
        stream.write(b"\x00")

    @staticmethod
    def __dump_head(stream, _id, typ):
        stream.write(struct.pack("<BI", typ, _id))

    @staticmethod
    def __dump(stream, _id, typ, value):
        TCPFormat.__dump_head(stream, _id, typ)
        stream.write(value)

    @staticmethod
    def __dump_pack(stream, _id, typ, pack, value):
        TCPFormat.__dump(stream, _id, typ, struct.pack(pack, value))

    @staticmethod
    def __dump_bool(stream, _id, item):
        TCPFormat.__dump_pack(stream, _id, 0, "<B", 1 if item else 0)

    @staticmethod
    def __dump_int(stream, _id, item):
        if item < 0:
            if item < -128:
                typ = (3, "<i")
            else:
                typ = (1, "<b")
        else:
            if item > 127:
                typ = (4, "<I")
            else:
                typ = (2, "<b")
        TCPFormat.__dump_pack(stream, _id, typ[0], typ[1], item)

    @staticmethod
    def __dump_float(stream, _id, item):
        TCPFormat.__dump_pack(stream, _id, 5, "<f", item)

    @staticmethod
    def __dump_str(stream, _id, item):
        TCPFormat.__dump_head(stream, _id, 6)
        TCPFormat.__dump_cstr(stream, item)

    @staticmethod
    def __dump_list(stream, _id, item):
        TCPFormat.__dump_head(stream, _id, 7)
        stream.write(struct.pack("<H", len(item)))
        for val in item:
            stream.write(struct.pack("<I", val))

    @staticmethod
    def __dump_dict(stream, _id, item):
        TCPFormat.__dump_head(stream, _id, 8)
        stream.write(struct.pack("<H", len(item)))
        for key, val in list(item.items()):
            stream.write(struct.pack("<I", val))
            TCPFormat.__dump_cstr(stream, key)
        stream.write(struct.pack("<H", 0))

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

    spelling = [
        "ActiveEffects",
        "BodyFlags",
        "Caps",
        "ClearedStatus",
        "Clip",
        "CurrAP",
        "CurrCell",
        "CurrHP",
        "CurrWeight",
        "CurrWorldspace",
        "CurrentHPGain",
        "Custom",
        "DateDay",
        "DateMonth",
        "DateYear",
        "Description",
        "Discovered",
        "Doors",
        "EffectColor",
        "Extents",
        "FavIconType",
        "HandleID",
        "HeadCondition",
        "HeadFlags",
        "Height",
        "HolotapePlaying",
        "InvComponents",
        "Inventory",
        "IsDataUnavailable",
        "IsInAnimation",
        "IsInAutoVanity",
        "IsInVats",
        "IsInVatsPlayback",
        "IsLoading",
        "IsMenuOpen",
        "IsPipboyNotEquipped",
        "IsPlayerDead",
        "IsPlayerInDialogue",
        "IsPlayerMovementLocked",
        "IsPlayerPipboyLocked",
        "LArmCondition",
        "LLegCondition",
        "ListVisible",
        "Local",
        "LocationFormId",
        "LocationMarkerFormId",
        "Locations",
        "Log",
        "Map",
        "MaxAP",
        "MaxHP",
        "MaxRank",
        "MaxWeight",
        "MinigameFormIds",
        "Modifier",
        "NEX",
        "NEY",
        "NWX",
        "NWY",
        "Name",
        "OnDoor",
        "PaperdollSection",
        "PerkPoints",
        "Perks",
        "Player",
        "PlayerInfo",
        "PlayerName",
        "PowerArmor",
        "QuestId",
        "Quests",
        "RArmCondition",
        "RLegCondition",
        "RadawayCount",
        "Radio",
        "Rank",
        "Rotation",
        "SWFFile",
        "SWX",
        "SWY",
        "Shared",
        "SlotResists",
        "SortMode",
        "Special",
        "StackID",
        "Stats",
        "Status",
        "StimpakCount",
        "TimeHour",
        "TorsoCondition",
        "TotalDamages",
        "TotalResists",
        "UnderwearType",
        "Value",
        "ValueType",
        "Version",
        "Visible",
        "Workshop",
        "WorkshopHappinessPct",
        "WorkshopOwned",
        "WorkshopPopulation",
        "World",
        "X",
        "XPLevel",
        "XPProgressPct",
        "Y",
        "canFavorite",
        "damageType",
        "diffRating",
        "equipState",
        "filterFlag",
        "formID",
        "inRange",
        "isLegendary",
        "isPowerArmorItem",
        "itemCardInfoList",
        "mapMarkerID",
        "radawayObjectID",
        "radawayObjectIDIsValid",
        "scaleWithDuration",
        "showAsPercent",
        "showIfZero",
        "sortedIDS",
        "statArray",
        "stimpakObjectID",
        "stimpakObjectIDIsValid",
        "taggedForSearch",
        "workshopData",
    ]

    @staticmethod
    def __load_string(stream):
        (length,) = struct.unpack("<I", stream.read(4))
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
        (typ,) = struct.unpack("<B", stream.read(1))
        if typ == 0:  # sint32_t
            (value,) = struct.unpack("<i", stream.read(4))
        elif typ == 1:  # uint32_t
            (value,) = struct.unpack("<I", stream.read(4))
        elif typ == 2:  # sint64_t
            (value,) = struct.unpack("<q", stream.read(8))
        elif typ == 3:  # float32_t
            (value,) = struct.unpack("<f", stream.read(4))
        elif typ == 4:  # float64_t
            (value,) = struct.unpack("<d", stream.read(8))
        elif typ == 5:  # boolean
            (value,) = struct.unpack("<B", stream.read(1))
            value = [False, True][value]
        elif typ == 6:  # string
            value = PipboyFormat.__load_string(stream)
        else:
            PipboyFormat.logger.error("Unknown Primitive Typ %d" % typ)
        return value

    @staticmethod
    def __load_array(stream):
        children = []
        (_count,) = struct.unpack("<I", stream.read(4))
        value = [None] * _count
        for _i in range(0, _count):
            (_index,) = struct.unpack("<I", stream.read(4))
            (_id, child) = PipboyFormat.__load_value(stream)
            value[_index] = _id
            children += child
        return (value, children)

    @staticmethod
    def __load_object(stream):
        children = []
        (_count,) = struct.unpack("<I", stream.read(4))
        value = {}
        for _i in range(0, _count):
            key = PipboyFormat.__load_key(stream)
            (_id, child) = PipboyFormat.__load_value(stream)
            value[key] = _id
            children += child
        return (value, children)

    @staticmethod
    def __load_value(stream):
        (typ, _id) = struct.unpack("<BI", stream.read(5))
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
        for name, subitem in list(item.items()):
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
            result = {
                k: BuiltinFormat.__dump_model(model, v) for k, v in list(result.items())
            }
        return result

    @staticmethod
    def dump_model(model):
        return BuiltinFormat.__dump_model(model, 0)
