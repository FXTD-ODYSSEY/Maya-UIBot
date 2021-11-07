# -*- coding: utf-8 -*-
"""

"""

from __future__ import absolute_import, division, print_function

from UIBot import UIParser
from maya import cmds, mel


class ShelfParser(UIParser):
    TYPE = "shelf"
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
        "label": "tooltip",
        "image1": "icon",
    }

    def parse(self, element):
        ui_set = set()
        layout = mel.eval("""$_=$gShelfTopLevel""")
        layout_path = cmds.shelfTabLayout(layout, q=1, fpn=1)
        labels = cmds.shelfTabLayout(layout, q=1, tl=1)
        for shelf in element.findall("widget"):
            object_name = shelf.attrib.get("name")
            if object_name.lower().startswith("stub"):
                continue
            attr_dict = {
                a.attrib["name"]: a.find("./").text for a in shelf.findall("attribute")
            }
            title = attr_dict.get("title")
            if not title:
                continue

            # NOTE delete shelf before create
            if title in labels:
                cmds.deleteUI("%s|%s" % (layout_path, title))
            ui_shelf = mel.eval("""$_=addNewShelfTab("%s")""" % title)
            ui_set.add(ui_shelf)
            # NOTE clear extra button
            for child in cmds.shelfLayout(ui_shelf, q=1, ca=1) or []:
                cmds.deleteUI(child)

            layout = shelf.find("layout")
            for item in layout.findall("./item/widget"):
                object_name = item.attrib.get("name")
                if object_name.lower().startswith("stub"):
                    continue
                config = self.parse_properties(item)
                config["parent"] = ui_shelf
                button = cmds.shelfButton(**config)
                ui_set.add(button)
        return ui_set

    def register(self):
        path = ".//widget[@class='QTabWidget'][@name='Shelf_Wgt']"
        element = self.root.find(path)
        ui_set = self.parse(element)
        return ui_set
