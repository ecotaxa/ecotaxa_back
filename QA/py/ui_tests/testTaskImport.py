import datetime
import json
import logging
import os
import time

from appli import db, app, g
from appli.database import Projects
from appli.tasks.taskmanager import Task, LoadTask


def create_db_task(task_class: str, param):
    new_db_task = Task()
    new_db_task.taskclass = task_class
    json_params = json.dumps(param)
    new_db_task.inputparam = json_params
    new_db_task.taskstep = 1
    db.session.add(new_db_task)
    db.session.commit()
    return new_db_task


#
# Permet de lancer la task dans le process courant, pour profiling et tests
#
def start_task_sync(taskid, forced_step=None):

    with app.app_context():  # Création d'un contexte pour utiliser les fonction GetAll,ExecSQL qui mémorisent
        g.db = None
        # logging.warning("Test Warning")
        # raise Exception("TEST")
        # On crée la tache à partir de la base
        aTask = LoadTask(taskid)
        # On s'assure de l'existence d'un répertoire dédié
        workingdir = aTask.GetWorkingDir()
        if not os.path.exists(workingdir):
            os.mkdir(workingdir)

        aTask.task.taskstate = "Running"
        if forced_step is not None:
            aTask.task.taskstep = forced_step
        # on execute SPCommon s'il existe
        fct = getattr(aTask, "SPCommon", None)
        if fct is not None:
            fct()
        # on execute le code du step associé
        fctname = "SPStep" + str(aTask.task.taskstep)
        fct = getattr(aTask, fctname, None)
        if fct is None:
            raise Exception("Procedure Missing :" + fctname)
        fct()


def test1():
    # On crée un projet vide car l'import dépend beaucoup des conditions initiales
    tps = time.time()
    prj = Projects()
    prj.title = "Test prj"
    db.session.add(prj)
    db.session.commit()
    params = {
      "steperrors": [],
      "InData": "/home/laurent/Devs/ecotaxa/SrvFics/task_24389_export_372_20190801_1246.zip",
      "ProjectId": prj.projid,
      "SkipAlreadyLoadedFile": "",
      "SkipObjectDuplicate": ""
    }
    db_task = create_db_task("TaskImport", param=params)
    task_id = db_task.id
    start_task_sync(task_id)
    # On n'a pas simulé la réponse aux questions donc on force le deuxième step
    start_task_sync(task_id, forced_step=2)
    tps = time.time() - tps
    logging.info("fini en %d", tps)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    if False:
        from pyinstrument import Profiler
        profiler = Profiler()
        profiler.start()
        # import cProfile
        # cProfile.run("test1()", "restats")
        # import pstats
        # p = pstats.Stats('restats')
        # p.sort_stats("cumulative").print_stats(100)
        test1()
        profiler.stop()
        print(profiler.output_text(unicode=True, color=True))
    else:
        test1()
