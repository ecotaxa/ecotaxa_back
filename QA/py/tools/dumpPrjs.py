import sys
from os.path import join, realpath, dirname
from pathlib import Path

from tech.AsciiDump import AsciiDumper

# Import services under test as a library
sys.path.extend([join("", "..", "..", "py")])

HERE = Path(dirname(realpath(__file__)))
TEST_CONFIG = HERE / ".." / "tests" / "link.ini"

# Import setup point
import link


def do_ref_ascii_dump(prjid: int, out_dump: str):
    sce = AsciiDumper()
    sce.run(projid=prjid, out=out_dump)


if __name__ == '__main__':
    # Dump prj1
    link.INI_DIR = HERE / ".." / "tests"
    link.INI_FILE = TEST_CONFIG
    do_ref_ascii_dump(1, "../tests/ref_227_prj1.txt")
    do_ref_ascii_dump(2, "../tests/ref_227_prj2.txt")
