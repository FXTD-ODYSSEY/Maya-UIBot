# -*- coding: utf-8 -*-
"""
UIBot Command
parse a ui file into a Maya Windows UI

============== Flag =====================
-r : -register [boolean]
regsiter the UI base on the UIBot.ui | False to deregister
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
import glob
import time
import json
import tempfile
from functools import partial
from functools import wraps
from itertools import chain
from collections import defaultdict
from xml.sax.saxutils import unescape

try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET

from maya import OpenMaya
from maya import OpenMayaMPx
from maya import cmds
from maya import mel

import six

LOGO = u"""
██╗   ██╗██╗██████╗  ██████╗ ████████╗
██║   ██║██║██╔══██╗██╔═══██╗╚══██╔══╝
██║   ██║██║██████╔╝██║   ██║   ██║   
██║   ██║██║██╔══██╗██║   ██║   ██║   
╚██████╔╝██║██████╔╝╚██████╔╝   ██║   
 ╚═════╝ ╚═╝╚═════╝  ╚═════╝    ╚═╝   
"""
nestdict = lambda: defaultdict(nestdict)

PLUGIN_NAME = "UIBot"
__file__ = globals().get("__file__")
__file__ = __file__ or cmds.pluginInfo(PLUGIN_NAME, q=1, p=1)
DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(DIR)
DIR not in sys.path and sys.path.insert(0, DIR)


def byteify(data):
    """
    https://stackoverflow.com/a/13105359
    unicode argument lead to error in python2
    """
    if six.PY3:
        return data
    if isinstance(data, dict):
        return {byteify(key): byteify(value) for key, value in data.iteritems()}
    elif isinstance(data, list):
        return [byteify(element) for element in data]
    elif isinstance(data, six.text_type):
        return data.encode("utf-8")
    else:
        return data


class UIParser(six.with_metaclass(abc.ABCMeta, object)):

    SCRIPT_FLAG = []

    def __init__(self, root, py_dict):
        self.root = root
        self.py_dict = py_dict

    def parse_script_flag(self, config, object_name="null"):
        msg = "`%s` cannot evaluate `%s`:`%s`"
        for flag in self.SCRIPT_FLAG:
            script = config.get(flag, "").strip()
            if script == "":
                continue

            if script.startswith("@") and ":" in script:
                scripts = script[1:].split(":")
                module_name = scripts[0]
                func_name = scripts[1]

                call = lambda *a, **kw: print(kw.get("msg", object_name))
                default_callback = partial(call, msg=msg % (object_name, flag, script))
                callback = self.py_dict.get(module_name)
                for attr in func_name.split("."):
                    callback = getattr(callback, attr, default_callback)
                config[flag] = callback if callable(callback) else default_callback
            else:
                config[flag] = script

    def parse_properties(self, element, mapping=None, prop="property"):
        CUSTOM = "custom"
        ATTRS = "attrs"
        mapping = mapping if mapping else {}
        menu_dict = defaultdict(dict)
        for p in element.findall(prop):
            prop_name = p.attrib["name"]
            stdset = p.attrib.get("stdset")
            attrs = CUSTOM if stdset else ATTRS
            child = p.find(".//")
            tag = child.tag
            value = child.text

            # NOTE iconset
            itr = child.itertext()
            while isinstance(value, str) and not value.strip():
                value = next(itr, "")
            value = value if value else ""

            # NOTE bool
            value = value == "true" if tag == "bool" else value
            menu_dict[attrs][prop_name] = value

        config = {}
        attrs = menu_dict.pop(ATTRS, {})
        for k, v in mapping.items():
            value = attrs.pop(v, None)
            if not value is None:
                config[k] = os.path.basename(value) if v == "icon" else value

        custom_attrs = menu_dict.pop(CUSTOM, {})
        _config = custom_attrs.pop("config", {})
        try:
            _config = byteify(json.loads(_config)) if _config else {}
        except json.JSONDecodeError:
            _config = {}
        config.update(_config)
        config.update(custom_attrs)

        return config

    @abc.abstractmethod
    def register(self):
        """register
        register the ui into MayaWindow
        """

    @classmethod
    def build(cls, ui_path, py_dict):
        """build

        :param ui_path: UIBot.ui path
        :type ui_path: str
        :param py_dict: name<=>module dict
        :type py_dict: dict
        :return: ui name list
        :rtype: list
        """
        tree = ET.parse(ui_path)
        root = tree.getroot()

        # NOTE load plaintext as empty module
        path = ".//widget/property[@name='plainText']/string"
        element = root.find(path)
        if hasattr(element, "text"):
            code = unescape(element.text)
            fp, path = tempfile.mkstemp()
            with open(path, "w") as f:
                f.write(code)
            py_dict[""] = imp.load_source("__UIBot_Internal_UI__", path)
            os.close(fp)
            os.remove(path)

        cls.widget_dict = {}
        for parser in cls.__subclasses__():
            res = parser(root, py_dict).register()
            cls.widget_dict[parser.__name__] = res if res else []

        return list(chain.from_iterable(cls.widget_dict.values()))


class Flag:
    """Command Flags"""

    REGISTER = "-r"
    REGISTER_LONG = "-register"
    HELP = "-h"
    HELP_LONG = "-help"


class UIBotCmd(OpenMayaMPx.MPxCommand):
    name = PLUGIN_NAME
    call = "callbacks"

    UI_LIST = []

    job_index = 0

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
        if parser.isQuery() and is_register:
            self.appendToResult(cls.UI_LIST)
            return

        if is_register:
            flag = parser.flagArgumentBool(Flag.REGISTER, 0)
            self.register_ui() if flag else self.clear_ui()
            self.appendToResult(cls.UI_LIST)

        # return self.redoIt(args)

    # def redoIt(self, args):
    #     pass

    # def undoIt(self, args):
    #     pass

    # def isUndoable(self):
    #     return True

    @classmethod
    def clear_ui(cls):
        for ui_name in cls.UI_LIST:
            if not ui_name:
                continue
            try:
                cmds.deleteUI(ui_name)
            except RuntimeError:
                pass

        cls.UI_LIST = []

    @classmethod
    def register_ui(cls):
        # NOTES(timmyliang) reset __subclasses__
        import UIBot

        imp.reload(UIBot)
        from UIBot import UIParser

        config_folders = [p for p in os.getenv("MAYA_UIBOT_PATH", "").split(";") if p]
        config_folders += [os.path.join(ROOT, "config")]

        ui_list = []
        py_dict = {}
        for config_folder in config_folders:
            for py in glob.iglob(os.path.join(config_folder, "*.py")):
                name = os.path.splitext(os.path.basename(py))[0]
                py_dict[name] = imp.load_source("__UIBot_%s__" % name, py)
            ui_path = os.path.join(config_folder, "*.ui")
            ui_list.extend([ui for ui in glob.iglob(ui_path)])

        if not ui_list:
            folders = "\n".join(config_folders)
            msg = "No ui file found under the path below\n%s" % folders
            OpenMaya.MGlobal.displayError(msg)
            return

        cls.clear_ui()
        for ui_path in ui_list:
            cls.UI_LIST.extend(UIParser.build(ui_path, py_dict))

    @classmethod
    def cmdCreator(cls):
        return OpenMayaMPx.asMPxPtr(cls())

    @classmethod
    def cmdSyntax(cls):
        syntax = OpenMaya.MSyntax()
        syntax.addFlag(Flag.REGISTER, Flag.REGISTER_LONG, OpenMaya.MSyntax.kBoolean)
        syntax.addFlag(Flag.HELP, Flag.HELP_LONG, OpenMaya.MSyntax.kUnsigned)
        syntax.enableEdit(0)
        syntax.enableQuery(1)
        return syntax

    @classmethod
    def on_plugin_register(cls):

        # NOTES(timmyliang) regsiter all UI
        cmds.UIBot(r=1)

        cls.job_index = cmds.scriptJob(
            runOnce=True,
            e=[
                "quitApplication",
                lambda: cmds.pluginInfo(PLUGIN_NAME, q=1, loaded=True)
                and cmds.unloadPlugin(PLUGIN_NAME),
            ],
        )
        print(LOGO)

    @classmethod
    def on_pluigin_deregister(cls):
        # NOTES(timmyliang) deregsiter all UI
        cmds.UIBot(r=0)
        if cmds.scriptJob(ex=cls.job_index):
            cmds.scriptJob(kill=cls.job_index)


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
