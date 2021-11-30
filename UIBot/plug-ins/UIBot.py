# -*- coding: utf-8 -*-
"""
UIBot

UIBot is NOT undoable, queryable, and NOT editable.
parse a ui file into a Maya Windows UI

============== Flag =====================
-r : -register [string]
regsiter the UI | string args
-d : -deregister [string]
deregsiter the UI
-p : -path [string] [multi]
refresh register path
-a : -auto [string]
set type to load after plugin initialize | "" means load nothing
-w : -widget [string]
get register ui data
-h : -help
display this help

============== Usage Example =====================
from maya import cmds
# NOTE register all ui
cmds.UIBot(r="all")
# NOTE query the register ui type list
cmds.UIBot(q=1,w=1)
# Result: [u'status', u'menu', u'shelf', u'toolbox'] #
# NOTE deregister menu ui
cmds.UIBot(d="menu")
"""

# Import future modules
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# Import built-in modules
import abc
from collections import defaultdict
from functools import partial
from functools import wraps
import glob
import imp
from itertools import chain
import json
import os
import sys
import time
from xml.sax.saxutils import unescape

# Import third-party modules
from maya import OpenMaya
from maya import OpenMayaMPx
from maya import cmds
import six


try:
    # Import built-in modules
    import xml.etree.cElementTree as ET
except ImportError:
    # Import built-in modules
    import xml.etree.ElementTree as ET

__author__ = "timmyliang"
__email__ = "820472580@qq.com"
__date__ = "2021-10-20 21:34:06"


LOGO = """
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
config_folder = os.path.join(ROOT, "config")


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
    TYPE = ""
    SCRIPT_FLAG = []
    MAPPING = {}

    def __init__(self, root, py_dict):
        self.root = root
        self.py_dict = py_dict

    def parse_script_flag(self, config, object_name="null"):
        """parse_script_flag [summary]

        Args:
            config ([type]): [description]
            object_name (str, optional): [description]. Defaults to "null".

        Returns:
            [type]: [description]
        """
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
        return config

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

        return self.parse_script_flag(config, element.attrib.get("name"))

    @abc.abstractmethod
    def register(self):
        """register
        register the ui into MayaWindow
        """

    @classmethod
    def build(cls, ui_path, py_dict, flag=""):
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
        path = ".//widget[@name='Module_PTE']/property[@name='plainText']/string"
        element = root.find(path)
        if hasattr(element, "text"):
            code = unescape(element.text)
            module = imp.new_module("__UIBot_Internal_Module__")
            six.exec_(code, module.__dict__)
            py_dict[""] = module

        widget_dict = {}
        for parser in cls.__subclasses__():
            res = []
            if parser.TYPE == flag or flag == "all":
                res = parser(root, py_dict).register()
            key = parser.TYPE if parser.TYPE else parser.__name__
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
    PATH = "-p"
    PATH_LONG = "-path"
    AUTO = "-a"
    AUTO_LONG = "-auto"
    HELP = "-h"
    HELP_LONG = "-help"


class Options:
    register = "_".join([PLUGIN_NAME, "register"])


class UIBotMixin(object):
    UI_DICT = {}
    PATHS = [config_folder] if os.path.isdir(config_folder) else []

    @classmethod
    def get_flag_arg(cls, parser, flag, flag_list, enable_none=False):
        f = parser.flagArgumentString(flag, 0)
        if enable_none and f == "":
            return ""
        flag_error_msg = "=>\nflag `%s` <=> `%s` not define \navailable flags {}"
        assert f in flag_list, flag_error_msg.format(flag_list) % (flag, f)
        return f

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
        if not flag:
            return
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

        ui_list = []
        py_dict = {}
        for folder in cls.PATHS:
            ui_path = os.path.join(folder, "*.ui")
            ui_list.extend(glob.glob(ui_path))
            for py in glob.iglob(os.path.join(folder, "*.py")):
                name = os.path.splitext(os.path.basename(py))[0]
                py_dict[name] = imp.load_source("__UIBot_%s__" % name, py)

        cls.deregister_ui(flag)
        for ui_path in ui_list:
            cls.UI_DICT.update(module.UIParser.build(ui_path, py_dict, flag))

    @classmethod
    def update_UI_DICT(cls):
        module = imp.load_source("UIBot", __file__)
        sys.modules["UIBot"] = module
        for path in cls.PATHS:
            for py in glob.iglob(os.path.join(path, "*.py")):
                imp.load_source("__UIBot_Module__", py)

        key_set = set()
        for parser in module.UIParser.__subclasses__():
            key = parser.TYPE if parser.TYPE else parser.__name__
            key_set.add(key)

        for k in cls.UI_DICT:
            if k not in key_set:
                cls.deregister_ui(k)
        for key in key_set:
            if key not in cls.UI_DICT:
                cls.UI_DICT[key] = []


class UIBotCmd(OpenMayaMPx.MPxCommand, UIBotMixin):
    name = PLUGIN_NAME
    job_index = 0

    @log_time
    def doIt(self, args):
        cls = self.__class__
        flag_list = ["all"] + list(cls.UI_DICT.keys())

        parser = OpenMaya.MArgParser(self.syntax(), args)

        is_flag_set = parser.isFlagSet
        is_register = is_flag_set(Flag.REGISTER) | is_flag_set(Flag.REGISTER_LONG)
        is_deregister = is_flag_set(Flag.DEREGISTER) | is_flag_set(Flag.DEREGISTER_LONG)
        is_widget = is_flag_set(Flag.WIDGET) | is_flag_set(Flag.WIDGET_LONG)
        is_path = is_flag_set(Flag.PATH) | is_flag_set(Flag.PATH_LONG)
        is_auto = is_flag_set(Flag.AUTO) | is_flag_set(Flag.AUTO_LONG)
        is_help = is_flag_set(Flag.HELP) | is_flag_set(Flag.HELP_LONG)

        num_flags = parser.numberOfFlagsUsed()
        if num_flags != 1 or is_help:
            OpenMaya.MGlobal.displayInfo(__doc__)
            return

        if parser.isQuery():
            res_list = cls.UI_DICT.keys()
            if is_auto:
                res_list = cmds.optionVar(q=Options.register)
            elif is_path:
                res_list = cls.PATHS
            self.appendToResult(res_list)
            return

        if is_path:
            num = parser.numberOfFlagUses(Flag.PATH)
            cls.PATHS = [parser.flagArgumentString(Flag.PATH, i) for i in range(num)]
            cls.update_UI_DICT()

        if is_auto:
            flag = cls.get_flag_arg(parser, Flag.AUTO, flag_list, True)
            cmds.optionVar(sv=[Options.register, flag])

        if is_widget:
            flag = cls.get_flag_arg(parser, Flag.WIDGET, flag_list)
            ui_list = cls.get_ui_list(flag, False)
            self.appendToResult(ui_list)

        elif is_register:
            flag = cls.get_flag_arg(parser, Flag.REGISTER, flag_list)
            self.register_ui(flag)
        elif is_deregister:
            flag = cls.get_flag_arg(parser, Flag.DEREGISTER, flag_list)
            self.deregister_ui(flag)

        # return self.redoIt(args)

    # def redoIt(self, args):
    #     pass

    # def undoIt(self, args):
    #     pass

    # def isUndoable(self):
    #     return True

    @classmethod
    def cmdCreator(cls):
        return OpenMayaMPx.asMPxPtr(cls())

    @classmethod
    def cmdSyntax(cls):
        syntax = OpenMaya.MSyntax()
        syntax.addFlag(Flag.REGISTER, Flag.REGISTER_LONG, OpenMaya.MSyntax.kString)
        syntax.addFlag(Flag.DEREGISTER, Flag.DEREGISTER_LONG, OpenMaya.MSyntax.kString)
        syntax.addFlag(Flag.WIDGET, Flag.WIDGET_LONG, OpenMaya.MSyntax.kString)
        syntax.addFlag(Flag.AUTO, Flag.AUTO_LONG, OpenMaya.MSyntax.kString)
        syntax.addFlag(Flag.PATH, Flag.PATH_LONG, OpenMaya.MSyntax.kStringObjects)
        syntax.addFlag(Flag.HELP, Flag.HELP_LONG)
        syntax.makeFlagMultiUse(Flag.PATH)
        syntax.enableEdit(0)
        syntax.enableQuery(1)
        return syntax

    @classmethod
    def on_plugin_register(cls):

        paths = os.getenv("MAYA_UIBOT_PATH", "").split(";")
        cls.PATHS += list({p for p in paths if os.path.isdir(p)})
        cls.update_UI_DICT()
        print(cls.UI_DICT)

        if not cmds.optionVar(exists=Options.register):
            cmds.optionVar(sv=(Options.register, "all"))
        flag = cmds.optionVar(q=Options.register)
        if flag:
            cmds.UIBot(r=flag)

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
