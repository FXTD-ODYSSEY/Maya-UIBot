# -*- coding: utf-8 -*-
"""

"""

from __future__ import absolute_import, division, print_function


from UIBot import UIParser
from maya import cmds, mel


class StatusParser(UIParser):
    FLAG = "status"
    def parse(self, element):
        pass

    def register(self):
        return []
