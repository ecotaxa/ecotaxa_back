import sys
from os.path import join

# Import services under test as a library
sys.path.extend([join("..", "..", "..", "py")])

import logging

logging.basicConfig(level=logging.INFO)


def do_dump():
    from tech.AsciiDump import AsciiDumper
    sce = AsciiDumper()
    # Dump after an import thru legacy 2.2 and empty DB
    #sce.run(projid=1,out="ref.txt")
    sce.run(projid=1,out="new.txt")


if __name__ == '__main__':
    do_dump()
