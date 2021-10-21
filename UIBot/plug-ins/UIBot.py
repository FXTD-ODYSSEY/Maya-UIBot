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

from maya import OpenMaya, OpenMayaMPx
import pymel.core as pm

from xml.dom import minidom

try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET


class UIParser(object):

    root = None

    @classmethod
    def register_menu(cls):

        return []

    @classmethod
    def register_status_line(cls):
        pass
        return []

    @classmethod
    def register_shelf(cls):
        pass
        return []

    @classmethod
    def register_toolbox(cls):
        pass
        return []

    @classmethod
    def load_ui(cls, ui_file, func_module):

        tree = ET.parse(ui_file)
        cls.root = tree.getroot()

        # TODO parse ui file to widgets
        widgets = []
        widgets += cls.register_menu()
        widgets += cls.register_status_line()
        widgets += cls.register_shelf()
        widgets += cls.register_toolbox()

        return widgets


# # NOTES(timmyliang) command flags
class Flag:
    REGISTER = "-r"
    REGISTER_LONG = "-register"
    TOOLBOX = "-t"
    TOOLBOX_LONG = "-toolbox"
    HELP = "-h"
    HELP_LONG = "-help"


class UIBotCmd(OpenMayaMPx.MPxCommand):
    name = "UIBot"
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

        # NOTE ================================================

        if is_register:
            flag = parser.flagArgumentBool(Flag.REGISTER, 0)
            cls.UI_LIST = self.register_ui(flag)
        elif is_toolbox:
            flag = parser.flagArgumentBool(Flag.TOOLBOX, 0)
            cls.TOOLBOX = self.register_toolbox(flag)

        # return self.redoIt(args)

    # def redoIt(self, args):
    #     pass

    # def undoIt(self, args):
    #     pass

    # def isUndoable(self):
    #     return True

    @classmethod
    def register_ui(cls, flag=True):
        if not flag:
            for ui in cls.UI_LIST:
                pm.deleteUI(ui)
            return []

        DIR = os.path.dirname(os.path.abspath(pm.pluginInfo(cls.name, q=1, p=1)))
        ROOT = os.path.dirname(DIR)
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
            func_module = imp.load_source("__UIBot_func__", call_path)
            return UIParser.load_ui(ui_path, func_module)

    @classmethod
    def register_toolbox(cls, flag=True):
        if not flag:
            if cls.TOOLBOX:
                pm.deleteUI(cls.TOOLBOX)
            return ""
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
        if not pm.optionVar(exists=cls.OPTION):
            pm.optionVar(iv=(cls.OPTION, 1))
        if pm.optionVar(q=cls.OPTION):
            pm.UIBot(t=1)

        # NOTES(timmyliang) regsiter all UI
        pm.UIBot(r=1)

    @classmethod
    def on_pluigin_deregister(cls):
        # NOTES(timmyliang) deregsiter all UI
        pm.UIBot(r=0)
        pm.UIBot(t=0)


# Initialize the script plug-in
def initializePlugin(mobject):
    mplugin = OpenMayaMPx.MFnPlugin(mobject)
    try:
        mplugin.registerCommand(UIBotCmd.name, UIBotCmd.cmdCreator, UIBotCmd.cmdSyntax)
    except:
        sys.stderr.write("Failed to register command: %s\n" % UIBotCmd.name)
        raise

    pm.evalDeferred(UIBotCmd.on_plugin_register, lp=1)


# Uninitialize the script plug-in
def uninitializePlugin(mobject):
    mplugin = OpenMayaMPx.MFnPlugin(mobject)

    UIBotCmd.on_pluigin_deregister()
    try:
        mplugin.deregisterCommand(UIBotCmd.name)
    except:
        sys.stderr.write("Failed to unregister command: %s\n" % UIBotCmd.name)
        raise


if __name__ == "__main__":
    pass
