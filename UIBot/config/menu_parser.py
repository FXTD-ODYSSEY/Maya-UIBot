# -*- coding: utf-8 -*-
"""

"""

from __future__ import absolute_import, division, print_function

from collections import defaultdict

from maya import cmds, mel
from UIBot import UIParser


class MenuParser(UIParser):
    TYPE = "menu"
    SCRIPT_FLAG = [
        "c",
        "command",
        "ddc",
        "dragDoubleClickCommand",
        "dmc",
        "dragMenuCommand",
        "pmc",
        "postMenuCommand",
        # NOTE optionBox trigger
        "optionBoxCommand",
    ]

    MAPPING = {
        "tearOff": "tearOffEnabled",
        "label": "title",
        "enable": "enabled",
        "image": "icon",
    }

    def __init__(self, root, py_dict):
        super(MenuParser, self).__init__(root, py_dict)
        self.menu_dict = []
        self.action_dict = []

    def parse(self, element):
        # NOTES(timmyliang) action attrs
        menu_list = []
        for a in element.findall("./addaction"):
            name = a.attrib.get("name")
            if name.lower().startswith("stub"):
                continue
            action = self.action_dict.get(name)
            is_action = not action is None
            menu = self.menu_dict.get(name)
            is_menu = not menu is None
            is_separator = name == "separator"

            data = defaultdict(dict)
            data["object_name"] = name
            data["class"] = "QAction"
            if is_action:
                data["config"] = self.parse_properties(action)
            elif is_menu:
                data["class"] = "QMenu"
                data["config"] = self.parse_properties(menu)
                data["items"] = self.parse(menu)
            elif is_separator:
                data["config"]["divider"] = True

            menu_list.append(data)

        return menu_list

    def create_ui(self, tree, parent):
        ui_set = set()
        for data in tree:
            object_name = data.get("object_name", "")
            config = data.get("config", {})
            cls = data.get("class", "QAction")

            if cls == "QMenu":
                if parent == "MayaWindow":
                    menu = cmds.menu(object_name, parent=parent, **config)
                else:
                    menu = cmds.menuItem(object_name, parent=parent, sm=1, **config)
                ui_set.add(menu)
                ui_set.update(self.create_ui(data.get("items", []), menu))
            if cls == "QAction":
                option_box = config.pop("optionBox", None)
                option_box_icon = config.pop("optionBoxIcon", None)
                option_box_command = config.pop("optionBoxCommand", None)
                action = cmds.menuItem(object_name, parent=parent, **config)
                ui_set.add(action)

                if option_box:
                    config = {"optionBox": option_box}
                    if not option_box_icon is None:
                        config["optionBoxIcon"] = option_box_icon
                    if not option_box_command is None:
                        config["command"] = option_box_command
                    action = cmds.menuItem(object_name, parent=parent, **config)
                    ui_set.add(action)
        return ui_set

    def register(self):
        path = ".//widget[@class='QMenu']"
        self.menu_dict = {m.attrib.get("name"): m for m in self.root.findall(path)}
        path = ".//action"
        self.action_dict = {a.attrib.get("name"): a for a in self.root.findall(path)}
        bar = self.root.find(".//widget[@class='QMenuBar'][@name='Menu_Bar']")
        tree = self.parse(bar)
        # return []
        # NOTES(timmyliang) dump tree data for debuging
        # with open(os.path.join(DIR, "data.json"), "w") as f:
        #     json.dump(tree, f, ensure_ascii=False, indent=4)

        maya_window = mel.eval("$_=$gMainWindow")
        return self.create_ui(tree, maya_window)
