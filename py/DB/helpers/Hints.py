# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2026  Picheral, Colin, Irisson (UPMC-CNRS)
#

# Hint preventing FTS on big tables
# Kills performance on some projects: "/*+ Leading(sam acq obh) NestLoop(sam acq obh) IndexOnlyScan(obh) IndexOnlyScan(obf) */"
# RECURS_HINT = "/*+ IndexOnlyScan(obh) IndexOnlyScan(obf) */"
RECURS_HINT = ""
