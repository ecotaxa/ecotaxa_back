# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from enum import Enum


class LicenseEnum(str, Enum):
    CC0 = "CC0"
    CC_BY = "CC BY 4.0"
    CC_BY_SA = "CC BY-SA 4.0"
    CC_BY_NC = "CC BY-NC 4.0"
    CC_BY_NC_SA = "CC BY-NC-SA 4.0"
    CC_BY_ND = "CC BY-ND 4.0"
    CC_BY_NC_ND = "CC BY-NC-ND 4.0"
    C = "C"


class DataLicense(object):
    """
        The license applied to data inside a project.
    """
    EXPLANATIONS = {LicenseEnum.CC0: "https://creativecommons.org/publicdomain/",
                    LicenseEnum.CC_BY: "https://creativecommons.org/licenses/by/4.0/ ",
                    LicenseEnum.CC_BY_SA: "https://creativecommons.org/licenses/by-sa/4.0/",
                    LicenseEnum.CC_BY_NC: "https://creativecommons.org/licenses/by-nc/4.0/",
                    LicenseEnum.CC_BY_NC_SA: "https://creativecommons.org/licenses/by-nc-sa/4.0/",
                    LicenseEnum.CC_BY_ND: "https://creativecommons.org/licenses/by-nd/4.0/",
                    LicenseEnum.CC_BY_NC_ND: "https://creativecommons.org/licenses/by-nc-nd/4.0/",
                    LicenseEnum.C: "All rights reserved"}
