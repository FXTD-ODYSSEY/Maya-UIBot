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


class ToolBoxParser(UIParser):
    TYPE = "toolbox"
    SCRIPT_FLAG = [
        "c",
        "command",
        "dcc",
        "doubleClickCommand",
        "dgc",
        "dragCallback",
        "dpc",
        "dropCallback",
        "hnd",
        "handleNodeDropCallback",
        "lec",
        "labelEditingCallback",
        "vcc",
        "visibleChangeCommand",
    ]

    MAPPING = {
        "label": "text",
        "image1": "icon",
    }

    def parse(self, element):
        ui_set = set()
        toolbox = mel.eval("$_=$gToolBox")
        for child in element.findall("./layout/item/widget"):
            object_name = child.attrib.get("name")
            if object_name.lower().startswith("stub"):
                continue
            config = self.parse_properties(child)
            config["parent"] = toolbox
            button = cmds.iconTextButton(**config)
            ui_set.add(button)

        return ui_set

    def register(self):
        path = ".//widget[@class='QGroupBox'][@name='Tool_Box_Group']"
        element = self.root.find(path)
        ui_set = self.parse(element)
        return ui_set
