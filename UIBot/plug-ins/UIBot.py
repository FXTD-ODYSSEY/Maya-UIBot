# -*- coding: utf-8 -*-
"""
UIBot Command
parse a ui file into a Maya Windows UI

============== Flag =====================
-r : -register [string]
regsiter the UI | string args 
-d : -deregister [string]
deregsiter the UI 
-w : -widget [string]
get register ui data
-h : -help 
display this help

============== Usage Example =====================
from maya import cmds
# NOTE register command 
cmds.UIBot(r="all")
# NOTE query the register ui list
cmds.UIBot(q=1,w=1)
# Result: [u'all', u'status', u'menu', u'shelf', u'toolbox'] # 
"""

from __future__ import absolute_import, division, print_function

import abc
import glob
import imp
import json
import os
import sys
import tempfile
import time
from collections import defaultdict
from functools import partial, wraps
from itertools import chain
from xml.sax.saxutils import unescape

import six

from maya import OpenMaya, OpenMayaMPx, cmds

try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET

__author__ = "timmyliang"
__email__ = "820472580@qq.com"
__date__ = "2021-10-20 21:34:06"


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


def log_time(func=None, msg="elapsed time:"):
    if not func:
        return partial(log_time, msg=msg)

    @wraps(func)
    def wrapper(*args, **kwargs):
        curr = time.time()
        res = func(*args, **kwargs)
        print(msg, time.time() - curr)
        return res

    return wrapper


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
    FLAG = ""
    SCRIPT_FLAG = []
    MAPPING = {}

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
        mapping = mapping if mapping else self.MAPPING
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
    def build(cls, ui_path, py_dict, flag="all"):
        """build

        :param ui_path: UIBot.ui path
        :type ui_path: str
        :param py_dict: name<=>module dict
        :type py_dict: dict
        :param flag: register specific type parser, defaults to "all"
        :type flag: str, optional
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

        widget_dict = {}
        for parser in cls.__subclasses__():
            res = []
            if parser.FLAG == flag or flag == "all":
                res = parser(root, py_dict).register()
            key = parser.FLAG if parser.FLAG else parser.__name__
            widget_dict[key] = list(res)

        return widget_dict


class Flag:
    """Command Flags"""

    REGISTER = "-r"
    REGISTER_LONG = "-register"
    DEREGISTER = "-d"
    DEREGISTER_LONG = "-deregister"
    WIDGET = "-w"
    WIDGET_LONG = "-widgets"
    HELP = "-h"
    HELP_LONG = "-help"


class UIBotCmd(OpenMayaMPx.MPxCommand):
    name = PLUGIN_NAME
    UI_DICT = {}
    job_index = 0

    @log_time
    def doIt(self, args):
        cls = self.__class__
        flag_list = ["all"] + cls.UI_DICT.keys()
        flag_error_msg = "`%s` not define | available flags {}".format(flag_list)
        # print(args)

        parser = OpenMaya.MArgParser(self.syntax(), args)
        is_flag_set = parser.isFlagSet

        num_flags = parser.numberOfFlagsUsed()
        is_help = is_flag_set(Flag.HELP) | is_flag_set(Flag.HELP_LONG)
        if num_flags != 1 or is_help:
            OpenMaya.MGlobal.displayInfo(__doc__)
            return

        if parser.isQuery():
            self.appendToResult(flag_list)
            return

        is_ui = is_flag_set(Flag.WIDGET) | is_flag_set(Flag.WIDGET_LONG)
        if is_ui:
            flag = parser.flagArgumentString(Flag.WIDGET, 0)
            assert flag in flag_list, flag_error_msg % flag
            ui_list = cls.get_ui_list(flag, False)
            self.appendToResult(ui_list)
            return

        is_register = is_flag_set(Flag.REGISTER) | is_flag_set(Flag.REGISTER_LONG)
        is_deregister = is_flag_set(Flag.DEREGISTER) | is_flag_set(Flag.DEREGISTER_LONG)
        if is_register:
            flag = parser.flagArgumentString(Flag.REGISTER, 0)
            assert flag in flag_list, flag_error_msg % flag
            self.register_ui(flag)
        elif is_deregister:
            flag = parser.flagArgumentString(Flag.DEREGISTER, 0)
            assert flag in flag_list, flag_error_msg % flag
            self.deregister_ui(flag)

        # return self.redoIt(args)

    # def redoIt(self, args):
    #     pass

    # def undoIt(self, args):
    #     pass

    # def isUndoable(self):
    #     return True

    @classmethod
    def get_ui_list(cls, flag, clear=True):
        if flag == "all":
            ui_list = list(chain.from_iterable(cls.UI_DICT.values()))
            if clear:
                cls.UI_DICT = {}
        else:
            ui_list = cls.UI_DICT[flag]
            if clear:
                cls.UI_DICT[flag] = []
        return ui_list

    @classmethod
    def deregister_ui(cls, flag="all"):
        ui_list = cls.get_ui_list(flag)
        for ui_name in ui_list:
            if not ui_name:
                continue
            try:
                cmds.deleteUI(ui_name)
            except RuntimeError:
                pass

    @classmethod
    def register_ui(cls, flag="all"):
        
        # NOTES(timmyliang) reset __subclasses__
        module = imp.load_source("UIBot", __file__)
        sys.modules["UIBot"] = module

        # TODO supprot loading path flag
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

        cls.deregister_ui(flag)
        for ui_path in ui_list:
            cls.UI_DICT.update(module.UIParser.build(ui_path, py_dict, flag))

    @classmethod
    def cmdCreator(cls):
        return OpenMayaMPx.asMPxPtr(cls())

    @classmethod
    def cmdSyntax(cls):
        syntax = OpenMaya.MSyntax()
        syntax.addFlag(Flag.REGISTER, Flag.REGISTER_LONG, OpenMaya.MSyntax.kString)
        syntax.addFlag(Flag.DEREGISTER, Flag.DEREGISTER_LONG, OpenMaya.MSyntax.kString)
        syntax.addFlag(Flag.WIDGET, Flag.WIDGET_LONG, OpenMaya.MSyntax.kString)
        syntax.addFlag(Flag.HELP, Flag.HELP_LONG, OpenMaya.MSyntax.kUnsigned)
        syntax.enableEdit(0)
        syntax.enableQuery(1)
        return syntax

    @classmethod
    def on_plugin_register(cls):
        
        # TODO optionVar for auto register flag
        
        # NOTES(timmyliang) regsiter all UI
        cmds.UIBot(r="all")

        cls.job_index = cmds.scriptJob(
            runOnce=True,
            e=["quitApplication", lambda: cmds.UIBot(d="all")],
        )
        print(LOGO)

    @classmethod
    def on_pluigin_deregister(cls):
        # NOTES(timmyliang) deregsiter all UI
        cmds.UIBot(d="all")
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
