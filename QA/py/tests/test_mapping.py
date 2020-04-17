# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#

from BO.Mappings import TableMapping

# noinspection PyUnresolvedReferences
from tests.config_fixture import config

MAPP = """n01=lat_end
n02=lon_end
n03=area
n04=mean
n05=stddev
n06=mode
n07=min
n08=max
n09=x
n10=y
n11=xm
n12=ym
n13=perim.
n14=bx
n15=by
n16=width
n17=height
n18=major
n19=minor
n20=angle
n21=circ.
n22=feret
n23=intden
n24=median
n25=skew
n26=kurt
n27=%area
n28=xstart
n29=ystart
n30=area_exc
n31=fractal
n32=skelarea
n33=slope
n34=histcum1
n35=histcum2
n36=histcum3
n37=xmg5
n38=ymg5
n39=nb1
n40=nb2
n41=nb3
n42=compentropy
n43=compmean
n44=compslope
n45=compm1
n46=compm2
n47=compm3
n48=symetrieh
n49=symetriev
n50=symetriehc
n51=symetrievc
n52=convperim
n53=convarea
n54=fcons
n55=thickr
n56=tag
n57=esd
n58=elongation
n59=range
n60=meanpos
n61=centroids
n62=cv
n63=sr
n64=perimareaexc
n65=feretareaexc
n66=perimferet
n67=perimmajor
n68=circex
n69=cdexc
t01=toto"""


def test_mapping1():
    a_mapping = TableMapping("mytbl")
    a_mapping.load_from_equal_list(MAPP)
    assert len(a_mapping) == 70
    assert a_mapping.max_by_type['n'] == 69
    assert a_mapping.max_by_type['t'] == 1
    a_mapping.add_column_for_table('lol', 't')
    assert a_mapping.max_by_type['t'] == 2
    enc: str = a_mapping.as_equal_list()
    assert enc.split("=") == (MAPP + "\nt02=lol").split("=")

MAPP2 = """n01=lat_end
n02=lon_end

n03=area

n04=mean
n05=stddev"""

def test_mapping2():
    a_mapping = TableMapping("mytbl")
    a_mapping.load_from_equal_list(MAPP2)
    assert len(a_mapping) == 5
    assert not a_mapping.is_empty()
