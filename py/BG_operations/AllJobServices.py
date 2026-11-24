# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2026  Picheral, Colin, Irisson (UPMC-CNRS)
#
"""
Manifest of modules containing JobServiceBase subclasses.

Job classes register themselves in JobServiceBase.__init_subclass__(), so importing
their module is enough. Keep this list in sync when adding a new job type in a new source file.
"""

import API_operations.Prediction  # noqa: F401
import API_operations.Subset  # noqa: F401
import API_operations.admin.NightlyJob  # noqa: F401
import API_operations.exports.DarwinCore  # noqa: F401
import API_operations.exports.ForProject  # noqa: F401
import API_operations.imports.Import  # noqa: F401
import API_operations.imports.SimpleImport  # noqa: F401
