# -*- coding: utf-8 -*-
"""
UIBot Command
parse a ui file into a Maya Windows UI

============== Flag =====================
-r : -register [boolean]
regsiter the UI base on the UIBot.ui | False to deregister
-t : -toolbox [boolean]
add the UIBot icon on the toolbox 
-h : -help 
display this help

============== Usage Example =====================
from maya import cmds
# NOTE register command 
cmds.UIBot(r=1)
# NOTE query the register ui list
cmds.UIBot(q=1,r=1)
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

__author__ = "timmyliang"
__email__ = "820472580@qq.com"
__date__ = "2021-10-20 21:34:06"

import os
import sys
import imp
import abc
import time
import json
from functools import partial
from functools import wraps
from itertools import chain
from collections import defaultdict

try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET

from maya import OpenMaya
from maya import OpenMayaMPx
from maya import cmds
from maya import mel


PLUGIN_NAME = "UIBot"
has__file__ = globals().get("__file__")
__file__ = has__file__ or cmds.pluginInfo(PLUGIN_NAME, q=1, p=1)
DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(DIR)

if has__file__:
    MODULE = os.path.join(ROOT, "scripts")
    sys.path.insert(0, MODULE) if MODULE not in sys.path else None

import six

nested_dict = lambda: defaultdict(nested_dict)


def logTime(func=None, msg="elapsed time:"):
    if not func:
        return partial(logTime, msg=msg)

    @wraps(func)
    def wrapper(*args, **kwargs):
        curr = time.time()
        res = func(*args, **kwargs)
        print(msg, time.time() - curr)
        return res

    return wrapper


class UIParser(six.with_metaclass(abc.ABCMeta, object)):
    def __init__(self, root, func_module):
        self.root = root
        self.func_module = func_module

    @abc.abstractmethod
    def parse(self, element):
        """parse
        parse the elementTree object to dict
        """

    @abc.abstractmethod
    def register(self):
        """register
        register the ui into MayaWindow
        """

    @classmethod
    def build(cls, ui_path, call_path):
        """build

        :param ui_path: UIBot.ui path
        :type ui_path: str
        :param call_path: callbacks.py path
        :type call_path: str
        :return: ui name list
        :rtype: list
        """
        tree = ET.parse(ui_path)
        root = tree.getroot()
        func_module = imp.load_source("__UIBot_func__", call_path)
        widget_dict = {}
        for parser in cls.__subclasses__():
            res = parser(root, func_module).register()
            widget_dict[parser.__name__] = res if res else []
        return list(chain.from_iterable(widget_dict.values()))


class MenuParser(UIParser):

    CUSTOM = "custom_attrs"
    ATTRS = "attrs"

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

    def __init__(self, root, func_module):
        super(MenuParser, self).__init__(root, func_module)
        self.menu_dict = []
        self.action_dict = []

    def parse_attrs(self, menu_dict, element):
        for p in element.findall("./property"):
            prop = p.attrib["name"]
            stdset = p.attrib.get("stdset")
            attrs = self.CUSTOM if stdset else self.ATTRS
            child = p.find(".//")
            tag = child.tag
            value = child.text

            # NOTE iconset
            itr = child.itertext()
            while isinstance(value, str) and not value.strip():
                value = itr.next()
            value = value if value else ""

            # NOTE bool
            value = value == "true" if tag == "bool" else value
            menu_dict[attrs][prop] = value

        config = {}
        attrs = menu_dict.pop(self.ATTRS, {})
        config["tearOff"] = attrs.pop("tearOffEnabled", None)
        config["label"] = attrs.pop("title", attrs.pop("text", None))
        config["enable"] = attrs.pop("enabled", None)
        icon = attrs.pop("icon", None)
        icon = os.path.basename(icon) if icon else None
        config["image"] = icon

        for k, v in config.copy().items():
            if v is None:
                config.pop(k)

        custom_attrs = menu_dict.pop(self.CUSTOM, {})
        _config = custom_attrs.pop("config", {})
        try:
            _config = json.loads(_config) if _config else {}
        except:
            _config = {}
        config.update(_config)
        config.update(custom_attrs)

        if config:
            menu_dict["config"] = config

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
                self.parse_attrs(data, action)
            elif is_menu:
                data["class"] = "QMenu"
                self.parse_attrs(data, menu)
                data["items"] = self.parse(menu)
            elif is_separator:
                data["config"]["divider"] = True

            menu_list.append(data)

        return menu_list

    def create_ui(self, tree, parent):
        ui_set = set()
        msg = "cannot find callback `%s`"
        func_module = self.func_module
        for data in tree:
            object_name = data.get("object_name", "")
            config = data.get("config", {})
            cls = data.get("class", "QAction")

            # NOTE script flag
            for flag in self.SCRIPT_FLAG:
                script = config.get(flag, "").strip()
                if script == "":
                    continue
                elif script.startswith("`") and script.endswith("`"):
                    config[flag] = script[1:-1]
                    continue
                callback = lambda *a, **kw: print(msg % kw.get("call"))
                default_callback = partial(callback, call=script)
                callback = func_module
                for attr in script.split("."):
                    callback = getattr(callback, attr, default_callback)
                config[flag] = callback if callable(callback) else default_callback

            if cls == "QMenu":
                if parent == "MayaWindow":
                    menu = cmds.menu(object_name, parent=parent, **config)
                else:
                    menu = cmds.menuItem(object_name, parent=parent, sm=1, **config)
                ui_set.add(menu)
                ui_set.update(self.create_ui(data.get("items", []), menu))
            if cls == "QAction":
                optionBox = config.pop("optionBox", None)
                optionBoxIcon = config.pop("optionBoxIcon", None)
                optionBoxCommand = config.pop("optionBoxCommand", None)
                action = cmds.menuItem(object_name, parent=parent, **config)
                ui_set.add(action)

                if optionBox:
                    config = {"optionBox": optionBox}
                    if not optionBoxIcon is None:
                        config["optionBoxIcon"] = optionBoxIcon
                    if not optionBoxCommand is None:
                        config["command"] = optionBoxCommand
                    action = cmds.menuItem(object_name, parent=parent, **config)
                    ui_set.add(action)
        return ui_set

    @logTime
    def register(self):
        path = ".//widget[@class='QMenu']"
        self.menu_dict = {m.attrib.get("name"): m for m in self.root.findall(path)}
        path = ".//action"
        self.action_dict = {a.attrib.get("name"): a for a in self.root.findall(path)}
        bar = self.root.find(".//widget[@class='QMenuBar'][@name='Menu_Bar']")
        tree = self.parse(bar)

        # NOTES(timmyliang) dump tree data for debuging
        # with open(os.path.join(DIR, "data.json"), "w") as f:
        #     json.dump(tree, f, ensure_ascii=False, indent=4)

        maya_window = mel.eval("$_=$gMainWindow")
        ui_list = self.create_ui(tree, maya_window)
        print("ui_list", ui_list)
        return ui_list


class StatusParser(UIParser):
    def parse(self, element):
        pass

    def register(self):
        return []


class ShelfParser(UIParser):
    def parse(self, element):
        pass

    def register(self):
        return []


class ToolBoxParser(UIParser):
    def parse(self, element):
        pass

    def register(self):
        return []


# ! ==========================================================================


class Flag:
    """ Command Flags"""

    REGISTER = "-r"
    REGISTER_LONG = "-register"
    TOOLBOX = "-t"
    TOOLBOX_LONG = "-toolbox"
    HELP = "-h"
    HELP_LONG = "-help"


class UIBotCmd(OpenMayaMPx.MPxCommand):
    name = PLUGIN_NAME
    call = "callbacks"

    UI_LIST = []
    TOOLBOX = ""

    OPTION = "UIBot_Toolbox"

    # def __init__(self):
    #     super(UIBotCmd, self).__init__()

    def doIt(self, args):
        cls = self.__class__

        parser = OpenMaya.MArgParser(self.syntax(), args)
        is_flag_set = parser.isFlagSet

        num_flags = parser.numberOfFlagsUsed()
        is_help = is_flag_set(Flag.HELP) | is_flag_set(Flag.HELP_LONG)
        if num_flags != 1 or is_help:
            OpenMaya.MGlobal.displayInfo(__doc__)
            return

        is_register = is_flag_set(Flag.REGISTER) | is_flag_set(Flag.REGISTER_LONG)
        is_toolbox = is_flag_set(Flag.TOOLBOX) | is_flag_set(Flag.TOOLBOX_LONG)
        if parser.isQuery():
            if is_register:
                self.appendToResult(cls.UI_LIST)
            if is_toolbox:
                self.appendToResult(cls.TOOLBOX)
            return

        if is_register:
            flag = parser.flagArgumentBool(Flag.REGISTER, 0)
            self.register_ui(flag)
            self.appendToResult(cls.UI_LIST)
        elif is_toolbox:
            flag = parser.flagArgumentBool(Flag.TOOLBOX, 0)
            self.register_toolbox(flag)
            self.appendToResult(cls.TOOLBOX)

        # return self.redoIt(args)

    # def redoIt(self, args):
    #     pass

    # def undoIt(self, args):
    #     pass

    # def isUndoable(self):
    #     return True

    @classmethod
    def delete_ui(cls, ui_name):
        if not isinstance(ui_name, str) or not ui_name:
            return
        try:
            cmds.deleteUI(ui_name)
        except RuntimeError:
            pass

    @classmethod
    def register_ui(cls, flag=True):
        if not flag:
            for ui in cls.UI_LIST:
                cls.delete_ui(ui)
            cls.UI_LIST = []
            return

        config_folder = os.getenv("MAYA_UIBOT_PATH") or os.path.join(ROOT, "config")
        call_path = os.path.join(config_folder, "%s.py" % cls.call)
        ui_path = os.path.join(config_folder, "%s.ui" % cls.name)

        is_call_exists = os.path.isfile(call_path)
        is_ui_exists = os.path.isfile(ui_path)
        if not is_call_exists:
            OpenMaya.MGlobal.displayError("call_path not exists %s" % call_path)
        elif not is_ui_exists:
            OpenMaya.MGlobal.displayError("ui_path not exists %s" % ui_path)
        else:
            # NOTES(timmyliang) clear ui
            cls.register_ui(False)
            ui_list = UIParser.build(ui_path, call_path)
            cls.UI_LIST = ui_list if ui_list else []

    @classmethod
    def register_toolbox(cls, flag=True):
        if not flag:
            cls.delete_ui(cls.TOOLBOX)
            cls.TOOLBOX = ""
            return
        # TODO create Toolbox icon

    @classmethod
    def cmdCreator(cls):
        return OpenMayaMPx.asMPxPtr(cls())

    @classmethod
    def cmdSyntax(cls):
        syntax = OpenMaya.MSyntax()
        syntax.addFlag(Flag.REGISTER, Flag.REGISTER_LONG, OpenMaya.MSyntax.kBoolean)
        syntax.addFlag(Flag.TOOLBOX, Flag.TOOLBOX_LONG, OpenMaya.MSyntax.kBoolean)
        syntax.addFlag(Flag.HELP, Flag.HELP_LONG, OpenMaya.MSyntax.kUnsigned)
        syntax.enableEdit(0)
        syntax.enableQuery(1)
        return syntax

    @classmethod
    def on_plugin_register(cls):
        # NOTES(timmyliang) initialize left toolbox icon
        if not cmds.optionVar(exists=cls.OPTION):
            cmds.optionVar(iv=(cls.OPTION, 1))
        if cmds.optionVar(q=cls.OPTION):
            cmds.UIBot(t=1)

        # NOTES(timmyliang) regsiter all UI
        cmds.UIBot(r=1)

    @classmethod
    def on_pluigin_deregister(cls):
        # NOTES(timmyliang) deregsiter all UI
        cmds.UIBot(r=0)
        cmds.UIBot(t=0)


# Initialize the script plug-in
def initializePlugin(mobject):
    mplugin = OpenMayaMPx.MFnPlugin(mobject)
    try:
        mplugin.registerCommand(UIBotCmd.name, UIBotCmd.cmdCreator, UIBotCmd.cmdSyntax)
    except:
        sys.stderr.write("Failed to register command: %s\n" % UIBotCmd.name)
        raise

    cmds.evalDeferred(UIBotCmd.on_plugin_register, lp=1)


# Uninitialize the script plug-in
def uninitializePlugin(mobject):
    mplugin = OpenMayaMPx.MFnPlugin(mobject)

    UIBotCmd.on_pluigin_deregister()
    try:
        mplugin.deregisterCommand(UIBotCmd.name)
    except:
        sys.stderr.write("Failed to unregister command: %s\n" % UIBotCmd.name)
        raise


# NOTES(timmyliang) Code Test
if __name__ == "__main__":
    UIBotCmd.register_ui()
