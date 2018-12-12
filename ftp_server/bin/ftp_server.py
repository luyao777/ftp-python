
#_*_coding:utf-8_*_

import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath('./')))
BASE_DIR_ = os.path.dirname(os.path.abspath('./'))
sys.path.append(BASE_DIR)
sys.path.append(BASE_DIR_)

import main

if __name__ == '__main__':
    main.ArvgHandler()