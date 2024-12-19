# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from enum import Enum
from typing import Final


class AccessLevelEnum(str, Enum):
    PUBLIC: Final = "1"
    OPEN: Final = "2"
    PRIVATE: Final = "0"


class LicenseEnum(str, Enum):
    CC0 = "CC0 1.0"
    CC_BY = "CC BY 4.0"
    # CC_BY_SA = "CC BY-SA 4.0"
    CC_BY_NC = "CC BY-NC 4.0"
    # CC_BY_NC_SA = "CC BY-NC-SA 4.0"
    # CC_BY_ND = "CC BY-ND 4.0"
    # CC_BY_NC_ND = "CC BY-NC-ND 4.0"
    Copyright = "Copyright"
    NO_LICENSE = ""


class DataLicense(object):
    """
    The license applied to data inside a project.
    """

    NAMES: Final = {
        LicenseEnum.CC0: "Public Domain Dedication",
        LicenseEnum.CC_BY: "Creative Commons Attribution 4.0 International Public License",
        # LicenseEnum.CC_BY_SA: "Creative Commons Attribution-ShareAlike 4.0 International Public License",
        LicenseEnum.CC_BY_NC: "Creative Commons Attribution-NonCommercial 4.0 International Public License",
        # LicenseEnum.CC_BY_NC_SA: "Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International Public License",
        # LicenseEnum.CC_BY_ND: "Creative Commons Attribution-NoDerivatives 4.0 International Public License",
        # LicenseEnum.CC_BY_NC_ND: "Creative Commons Attribution-NonCommercial-NoDerivatives 4.0 International Public License",
        LicenseEnum.Copyright: "All rights reserved",
        LicenseEnum.NO_LICENSE: "License not chosen yet",
    }

    SHORT_NAMES: Final = {
        LicenseEnum.CC0: "",
        LicenseEnum.CC_BY: "CC-BY",
        # LicenseEnum.CC_BY_SA: "CC-BY-SA",
        LicenseEnum.CC_BY_NC: "CC-BY-NC",
        # LicenseEnum.CC_BY_NC_SA: "CC-BY-NC-SA",
        # LicenseEnum.CC_BY_ND: "CC-BY-ND",
        # LicenseEnum.CC_BY_NC_ND: "CC-BY-ND",
        LicenseEnum.Copyright: "©",
        LicenseEnum.NO_LICENSE: "?",
    }

    EXPLANATIONS: Final = {
        LicenseEnum.CC0: r'<a href="https://creativecommons.org/publicdomain/zero/1.0/" rel="nofollow"><strong>CC-0</strong></a>: all registered EcoTaxa users are free to download, redistribute, modify, and build upon the data, with no conditions. Other databases can index the data. The data falls into the worldwide public domain. This is the license preferred by <a href="https://obis.org/manual/policy/" rel="nofollow">OBIS</a> and <a href="https://www.gbif.org/terms" rel="nofollow">GBIF</a>.',
        LicenseEnum.CC_BY: r'<a href="https://creativecommons.org/licenses/by/4.0/" rel="nofollow"><strong>CC-BY</strong></a>: all registered EcoTaxa users are free to download, redistribute, modify, and build upon the data, as long as they cite the dataset and its authors. Other databases can index the data.',
        # LicenseEnum.CC_BY_SA: "https://creativecommons.org/licenses/by-sa/4.0/",
        LicenseEnum.CC_BY_NC: r'<a href="https://creativecommons.org/licenses/by-nc/4.0/" rel="nofollow"><strong>CC-BY-NC</strong></a>: all registered EcoTaxa users are free to download, redistribute, modify, and build upon the data, as long as they cite the dataset and its authors, and do not use it for commercial purpose ("primarily intended for or directed toward commercial advantage or monetary compensation"). Other databases can index the data.',
        # LicenseEnum.CC_BY_NC_SA: "https://creativecommons.org/licenses/by-nc-sa/4.0/",
        # LicenseEnum.CC_BY_ND: "https://creativecommons.org/licenses/by-nd/4.0/",
        # LicenseEnum.CC_BY_NC_ND: "https://creativecommons.org/licenses/by-nc-nd/4.0/",
        LicenseEnum.Copyright: r"<strong>Copyright</strong>: only contributors to this project have rights on this data. This prevents its distribution in any kind of database.",
        LicenseEnum.NO_LICENSE: "Not chosen",
    }

    EXPORT_EXPLANATIONS: Final = {
        LicenseEnum.CC0: "https://creativecommons.org/publicdomain/zero/1.0/",
        LicenseEnum.CC_BY: "https://creativecommons.org/licenses/by/4.0/",
        # LicenseEnum.CC_BY_SA: "https://creativecommons.org/licenses/by-sa/4.0/",
        LicenseEnum.CC_BY_NC: "https://creativecommons.org/licenses/by-nc/4.0/",
        # LicenseEnum.CC_BY_NC_SA: "https://creativecommons.org/licenses/by-nc-sa/4.0/",
        # LicenseEnum.CC_BY_ND: "https://creativecommons.org/licenses/by-nd/4.0/",
        # LicenseEnum.CC_BY_NC_ND: "https://creativecommons.org/licenses/by-nc-nd/4.0/",
        LicenseEnum.Copyright: "All rights reserved",
        LicenseEnum.NO_LICENSE: "Not chosen",
    }

    RESTRICTION: Final = {
        LicenseEnum.CC0: 0,
        LicenseEnum.CC_BY: 1,
        # LicenseEnum.CC_BY_SA: 2,
        LicenseEnum.CC_BY_NC: 3,
        # LicenseEnum.CC_BY_NC_SA: 4,
        # LicenseEnum.CC_BY_ND: 5,
        # LicenseEnum.CC_BY_NC_ND: 6,
        LicenseEnum.Copyright: 7,
        LicenseEnum.NO_LICENSE: 8,
    }

    BY_RESTRICTION: Final = {lev: lic for lic, lev in RESTRICTION.items()}
