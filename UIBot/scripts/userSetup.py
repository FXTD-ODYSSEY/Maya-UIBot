# -*- coding: utf-8 -*-
"""
auto load UIBot plugin
"""

# Import future modules
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function


__author__ = "timmyliang"
__email__ = "820472580@qq.com"
__date__ = "2021-10-20 21:35:43"

# Import built-in modules
from functools import partial
import os

# Import third-party modules
from maya import cmds


if not cmds.about(q=1, batch=1):
    module_path = cmds.getModulePath(mn="UIBot")
    icon_path = os.path.join(module_path, "icons")
    XBMLANGPATH = os.environ["XBMLANGPATH"]
    if os.path.isdir(icon_path) and icon_path not in XBMLANGPATH.split(os.pathsep):
        os.environ["XBMLANGPATH"] = icon_path + os.pathsep + os.environ["XBMLANGPATH"]

    plugin_path = os.path.join(module_path, "plug-ins", "UIBot.py")
    if os.path.isfile(plugin_path):
        if not cmds.pluginInfo(plugin_path, q=1, loaded=1):
            cmds.evalDeferred(partial(cmds.loadPlugin, plugin_path), lp=1)
