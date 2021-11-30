# -*- coding: utf-8 -*-
"""

"""

# Import future modules
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# Import third-party modules
from UIBot import UIParser
from maya import cmds
from maya import mel


class StatusParser(UIParser):
    TYPE = "status"

    def parse(self, element):
        pass

    def register(self):
        return []
