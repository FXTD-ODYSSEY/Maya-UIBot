# -*- coding: utf-8 -*-
"""
call by UIBot.ui
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

__author__ = 'timmyliang'
__email__ = '820472580@qq.com'
__date__ = '2021-10-20 22:01:06'

def hello(*args):
    print("hello")
    

class OptionsBase(object):
    
    @staticmethod
    def options(*args):
        print("options")
    