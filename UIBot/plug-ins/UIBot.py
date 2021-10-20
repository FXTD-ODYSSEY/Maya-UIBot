# -*- coding: utf-8 -*-
"""
UIBot Command
parse a ui file into a Maya Windows UI

============== Flag =====================
-r : -register [boolean]
regsiter the UI base on the UIBot.ui | False to deregister
-t : -toolbar [boolean]
add the UIBot icon on the toolbar 
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
from collections import namedtuple

from maya import OpenMaya, OpenMayaMPx
import pymel.core as pm

# NOTES(timmyliang) command flags
REGISTER = "-r"
REGISTER_LONG = "-register"
TOOLBAR = "-t"
TOOLBAR_LONG = "-toolbar"
HELP = "-h"
HELP_LONG = "-help"
OPTION = "UIBot_Toolbar"

# class implementation for custom command
class UIBotCmd(OpenMayaMPx.MPxCommand):
    name = "UIBot"
    PROCESS = namedtuple("Process", "H R T")(0, 1, 2)
    UI_LIST = []
    TOOLBAR = ""

    def __init__(self):
        super(UIBotCmd, self).__init__()
        self.process = self.PROCESS.H

        DIR = os.path.dirname(os.path.abspath(pm.pluginInfo(self.name, q=1, p=1)))
        ROOT = os.path.dirname(DIR)
        config_folder = os.getenv("MAYA_UIBOT_PATH") or os.path.join(ROOT, "config")
        func_path = os.path.join(config_folder, "func.py")
        self.ui_path = os.path.join(config_folder, "UIBot.ui")
        # self.func_module = imp.load_source("__UIBot_func__", func_path)

    def isUndoable(self):
        return True

    def doIt(self, args):
        self.process = self.PROCESS.H
        parser = OpenMaya.MArgParser(self.syntax(), args)
        numFlags = parser.numberOfFlagsUsed()
        if numFlags != 1 or parser.isFlagSet(HELP) | parser.isFlagSet(HELP_LONG):
            OpenMaya.MGlobal.displayInfo(__doc__)
            return

        is_register = parser.isFlagSet(REGISTER) | parser.isFlagSet(REGISTER_LONG)
        if parser.isQuery() and is_register:
            self.appendToResult(self.__class__.UI_LIST)
            return

        is_toolbar = parser.isFlagSet(TOOLBAR) | parser.isFlagSet(TOOLBAR_LONG)
        if parser.isQuery() and is_toolbar:
            self.appendToResult(self.__class__.TOOLBAR)
            return

        # if is_register:
        #     self.process = self.PROCESS.R
        # elif is_toolbar:
        #     self.process = self.PROCESS.T
        # return self.redoIt(args)

    # def redoIt(self, args):
    #     pass

    # def undoIt(self, args):
    #     if self.process == self.PROCESS.R:
    #         pass

    @classmethod
    def cmdCreator(cls):
        return OpenMayaMPx.asMPxPtr(cls())

    @staticmethod
    def cmdSyntax():
        syntax = OpenMaya.MSyntax()
        syntax.addFlag(REGISTER, REGISTER_LONG, OpenMaya.MSyntax.kBoolean)
        syntax.addFlag(TOOLBAR, TOOLBAR_LONG, OpenMaya.MSyntax.kBoolean)
        syntax.addFlag(HELP, HELP_LONG, OpenMaya.MSyntax.kUnsigned)
        syntax.enableEdit(0)
        syntax.enableQuery(1)
        return syntax

    @staticmethod
    def on_plugin_init():
        # print("on_plugin_init")
        # NOTES(timmyliang) initialize left toolbar icon
        if not pm.optionVar(exists=OPTION):
            pm.optionVar(iv=(OPTION, 1))
        if pm.optionVar(q=OPTION) and not pm.UIBot(q=1, t=1):
            pm.UIBot(t=1)
        # NOTES(timmyliang) regsiter all UI
        not pm.UIBot(q=1, r=1) and pm.UIBot(r=1)

    @staticmethod
    def on_pluigin_uninit():
        # print("on_pluigin_uninit")
        # NOTES(timmyliang) deregsiter all UI
        pm.UIBot(q=1, r=1) and pm.UIBot(r=0)
        pm.UIBot(q=1, t=1) and pm.UIBot(t=0)


# Initialize the script plug-in
def initializePlugin(mobject):
    mplugin = OpenMayaMPx.MFnPlugin(mobject)
    try:
        mplugin.registerCommand(UIBotCmd.name, UIBotCmd.cmdCreator, UIBotCmd.cmdSyntax)
    except:
        sys.stderr.write("Failed to register command: %s\n" % UIBotCmd.name)
        raise

    pm.evalDeferred(UIBotCmd.on_plugin_init, lp=1)


# Uninitialize the script plug-in
def uninitializePlugin(mobject):
    mplugin = OpenMayaMPx.MFnPlugin(mobject)

    pm.evalDeferred(UIBotCmd.on_pluigin_uninit, lp=1)

    try:
        mplugin.deregisterCommand(UIBotCmd.name)
    except:
        sys.stderr.write("Failed to unregister command: %s\n" % UIBotCmd.name)
        raise
