# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from enum import Enum


class LicenseEnum(str, Enum):
    CC0 = "CC0 1.0"
    CC_BY = "CC BY 4.0"
    CC_BY_SA = "CC BY-SA 4.0"
    CC_BY_NC = "CC BY-NC 4.0"
    CC_BY_NC_SA = "CC BY-NC-SA 4.0"
    CC_BY_ND = "CC BY-ND 4.0"
    CC_BY_NC_ND = "CC BY-NC-ND 4.0"
    Copyright = "Copyright"


class DataLicense(object):
    """
        The license applied to data inside a project.
    """
    NAMES = {LicenseEnum.CC0: "Public Domain Dedication",
             LicenseEnum.CC_BY: "Creative Commons Attribution 4.0 International Public License",
             LicenseEnum.CC_BY_SA: "Creative Commons Attribution-ShareAlike 4.0 International Public License",
             LicenseEnum.CC_BY_NC: "Creative Commons Attribution-NonCommercial 4.0 International Public License",
             LicenseEnum.CC_BY_NC_SA: "Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International Public License",
             LicenseEnum.CC_BY_ND: "Creative Commons Attribution-NoDerivatives 4.0 International Public License",
             LicenseEnum.CC_BY_NC_ND: "Creative Commons Attribution-NonCommercial-NoDerivatives 4.0 International Public License",
             LicenseEnum.Copyright: "All rights reserved"}

    EXPLANATIONS = {LicenseEnum.CC0: "https://creativecommons.org/publicdomain/zero/1.0/",
                    LicenseEnum.CC_BY: "https://creativecommons.org/licenses/by/4.0/",
                    LicenseEnum.CC_BY_SA: "https://creativecommons.org/licenses/by-sa/4.0/",
                    LicenseEnum.CC_BY_NC: "https://creativecommons.org/licenses/by-nc/4.0/",
                    LicenseEnum.CC_BY_NC_SA: "https://creativecommons.org/licenses/by-nc-sa/4.0/",
                    LicenseEnum.CC_BY_ND: "https://creativecommons.org/licenses/by-nd/4.0/",
                    LicenseEnum.CC_BY_NC_ND: "https://creativecommons.org/licenses/by-nc-nd/4.0/",
                    LicenseEnum.Copyright: "All rights reserved"}
