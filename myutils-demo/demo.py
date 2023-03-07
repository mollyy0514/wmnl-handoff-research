#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
pdir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))  # for py-script
sys.path.insert(1, pdir)

# import myutils
from myutils import makedir

makedir('./testdir-py')
