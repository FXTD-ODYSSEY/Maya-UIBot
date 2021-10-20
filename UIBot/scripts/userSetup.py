# -*- coding: utf-8 -*-
"""
auto load UIBot plugin
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

__author__ = 'timmyliang'
__email__ = '820472580@qq.com'
__date__ = '2021-10-20 21:35:43'

from maya import cmds
from functools import partial

if not cmds.about(q=1,batch=1):
    plugin_name = "UIBot"
    if not cmds.pluginInfo(plugin_name,q=1,loaded=1):
        cmds.evalDeferred(partial(cmds.loadPlugin,plugin_name),lp=1)

    

