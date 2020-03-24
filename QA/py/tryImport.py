"""
Import a file using services (no API yet)
"""
import sys
from os.path import join

# Import services under test as a library
sys.path.extend([join("", "..", "..", "py")])

import logging

logging.basicConfig(level=logging.INFO)

if __name__ == '__main__':
    # Import services
    from crud.Project import ProjectService
    from crud.Task import TaskService

    prj_sce = ProjectService()
    task_sce = TaskService()
    from tasks.ImportStep1 import ImportStep1
    from tasks.ImportStep2 import ImportStep2

    # Do step1
    sce1 = ImportStep1()
    sce1.prj_id = prj_sce.create("Test LS")
    sce1.task_id = task_sce.create()
    sce1.input_path = "data/V6.zip"
    sce1.run()
    # Do step2
    sce2 = ImportStep2()
    sce2.mapping = sce1.mapping
    sce2.prj_id = sce1.prj_id
    sce2.task_id = sce1.task_id
    sce2.source_dir_or_zip = sce1.source_dir_or_zip
    # Map to admin
    sce2.found_users['elizandro rodriguez'] = {'id': 1}
    sce2.run()

    out_dump = "new.txt"
    print("All is in projet #%d, doing dump into %s" % (sce2.prj_id, out_dump))

    from tech.AsciiDump import AsciiDumper
    sce = AsciiDumper()
    sce.run(projid=sce2.prj_id, out=out_dump)
