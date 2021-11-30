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
import sys
import subprocess
from maya import cmds

try:
    import urllib.request as urllib2
except ImportError:
    import urllib2


MODULE_NAME = "UIBot"
VENDORS = {
    "Qt": "Qt.py",
    "six": "six",
}
mayapy = "%spy.exe" % os.path.splitext(sys.executable)[0]


class ModuleManager(object):
    @staticmethod
    def get_pip():
        try:
            import pip
        except ImportError:
            version = sys.version_info[:2]
            url = "https://bootstrap.pypa.io/pip/{}.{}/get-pip.py".format(*version)
            # TODO network error
            page = urllib2.urlopen(url)
            exec(page.read())
            import pip

        return pip

    @staticmethod
    def is_module_available(module):
        try:
            __import__(module)
        except ImportError:
            return False
        else:
            return True

    @classmethod
    def load_modules(cls, modules):
        need_imports = [p for m, p in modules if not cls.is_module_available(m)]
        if not need_imports:
            return

        cls.get_pip()
        print("start install dependencies:")
        print("\n".join(need_imports))
        print("-" * 20)
        for m in need_imports:
            commands = [mayapy, "-m", "pip", "install", m]
            status = subprocess.check_output(commands, shell=True)
            print(status)


def initialize():
    # ModuleManager.load_modules(VENDORS)

    module_path = cmds.getModulePath(mn=MODULE_NAME)
    icon_path = os.path.join(module_path, "icons")
    XBMLANGPATH = os.environ["XBMLANGPATH"]
    if os.path.isdir(icon_path) and icon_path not in XBMLANGPATH.split(os.pathsep):
        os.environ["XBMLANGPATH"] = icon_path + os.pathsep + os.environ["XBMLANGPATH"]

    plugin_path = os.path.join(module_path, "plug-ins", "%s.py" % MODULE_NAME)
    if os.path.isfile(plugin_path):
        if not cmds.pluginInfo(plugin_path, q=1, loaded=1):
            cmds.loadPlugin(plugin_path)


if __name__ == "__main__":
    if not cmds.about(q=1, batch=1):
        cmds.evalDeferred(initialize, lp=1)
