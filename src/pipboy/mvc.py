#!/usr/bin/env python

import logging
import re

from .format import BuiltinFormat


class Model(object):
    logger = logging.getLogger("pipboy.Model")

    server = {
        "info": {"lang": "en", "version": "1.1.30.0"},
        "run_server": False,
        "run_client": False,
    }

    __startup = {
        "Inventory": {},
        "Log": [],
        "Map": {},
        "Perks": [],
        "PlayerInfo": {},
        "Quests": [],
        "Radio": [],
        "Special": [],
        "Stats": {},
        "Status": {
            "EffectColor": [0.08, 1.0, 0.09],
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
            "IsPlayerPipboyLocked": False,
        },
        "Workshop": [],
    }

    def __clear(self):
        self.__path = {}
        self.__items = {}

    def __init__(self):
        super(Model, self).__init__()
        self.listener = {"update": [], "command": [], "map_update": []}
        self.load(BuiltinFormat.load(Model.__startup))

    def register(self, typ, function):
        self.listener[typ].append(function)

    def unregister(self, typ, function):
        if typ not in self.listener:
            self.logger.warn(
                "Could not remove function {func_name} from listener {listener}, listener did not exist.".format(
                    func_name=function.__name__, listener=typ
                )
            )
            return
        try:
            self.listener[typ].remove(function)
        except ValueError:
            self.logger.warn(
                "Could not remove function {func_name} from listener {listener}, function did not exist.".format(
                    func_name=function.__name__, listener=typ
                )
            )

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
        match = re.match("^(\.([a-zA-Z0-9]+)|\[([0-9]+)\])(.*)$", path)
        if match:
            item = self.get_item(_id)
            groups = match.groups()
            if groups[1] and type(item) == dict:
                for k, v in list(item.items()):
                    if k.lower() == groups[1].lower():
                        return self.__get_id(v, groups[3])
            elif groups[2] and type(item) == list:
                try:
                    idx = int(groups[2])
                    return self.__get_id(item[idx], groups[3])
                except Exception as e:
                    self.logger.error(str(e))
        return None

    def get_id(self, path):
        if path.startswith("$"):
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
                for k, v in list(value.items()):
                    self.__path[v] = (".%s" % k, _id)
        for func in self.listener["update"]:
            func(changed)

    def command(self, _type, args):
        for func in self.listener["command"]:
            func(_type, args)

    def map_update(self, data):
        for func in self.listener["map_update"]:
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
                for child in list(item.values()):
                    result += self.dump(child, recursive)
        result.append([_id, item])
        return result


class View(object):
    logger = logging.getLogger("pipboy.Console")

    ignore = [
        "$.PlayerInfo.TimeHour",
        "$.Map.Local.Player.X",
        "$.Map.Local.Player.Y",
        "$.Map.Local.Player.Rotation",
        "$.Map.World.Player.X",
        "$.Map.World.Player.Y",
        "$.Map.World.Player.Rotation",
    ]

    def __init__(self, model):
        self.model = model
        self.should_spam = True
        model.register("update", self.listen_update)
        model.register("command", self.listen_command)
        model.register("map_update", self.listen_map_update)

    def listen_update(self, items):
        """
        This listens and prints all new data, excluding those in the `ignore` list.
        :param items: list of items (ints)
        :return:
        """
        for item in items:
            if not isinstance(item, int):
                self.logger.debug("strange model.")
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
        print(("{type} {args}".format(type=_type, args=args)))

    def listen_map_update(self, data):
        """
        This function receives the data for the local map.
        :param data: the data
        """
        pass

    # noinspection PyMethodMayBeStatic
    def print_update(self, path, item):
        if self.should_spam:
            print(("{path} {value}".format(path=path, value=item)))
