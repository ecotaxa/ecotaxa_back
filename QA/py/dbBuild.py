"""
Build the DB from scratch in EcoTaxa V2_2
"""
import sys
from os.path import join

# Import services under test as a library
sys.path.extend([join("..", "..", "py")])
from lib.legacyProcesses import Manage

if __name__ == '__main__':
    Manage().run_create_db()
