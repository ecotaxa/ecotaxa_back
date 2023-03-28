# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
import pytest
from BO.Mappings import TableMapping, RemapOp
from DB import ObjectFields

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
    a_mapping = TableMapping(ObjectFields)
    a_mapping.load_from_equal_list(MAPP)
    assert len(a_mapping) == 70
    assert a_mapping.max_by_type("n") == 69
    assert a_mapping.max_by_type("t") == 1
    a_mapping.add_column_for_table("lol", "t")
    assert a_mapping.max_by_type("t") == 2
    enc: str = a_mapping.as_equal_list()
    assert enc.split("=") == (MAPP + "\nt02=lol").split("=")
    assert list(a_mapping.find_tsv_cols(["cdexc", "no", "toto"]).values()) == [
        "n69",
        "t01",
    ]


MAPP2 = """n01=lat_end
n02=lon_end

n03=area

n04=mean
n05=stddev"""


def test_mapping2():
    a_mapping = TableMapping(ObjectFields)
    a_mapping.load_from_equal_list(MAPP2)
    assert len(a_mapping) == 5
    assert not a_mapping.is_empty()


MAPP_DST = """n01=stddev
n02=lat_end
n03=mean
n04=area
n05=lon_end"""

MAPP_SRC = """n01=lat_end
n02=lon_end
n03=area
n04=mean
n05=stddev"""


def test_reshuff():
    src_mapping = TableMapping(ObjectFields)
    src_mapping.load_from_equal_list(MAPP_SRC)
    dst_mapping = TableMapping(ObjectFields)
    dst_mapping.load_from_equal_list(MAPP_DST)
    remap = src_mapping.transforms_from(dst_mapping)
    assert remap == [
        ("n01", "n05"),
        ("n02", "n01"),
        ("n03", "n04"),
        ("n04", "n03"),
        ("n05", "n02"),
    ]


def test_overflow():
    """
    Check that if there are too many fields, it fails.
    """
    a_mapping = TableMapping(ObjectFields)
    a_mapping.load_from_equal_list(MAPP2)
    # OK we have 5 'n' fields, let's add 495 more
    for n in range(495):
        ok_added = a_mapping.add_column_for_table("fl%dd" % n, "n")
        assert ok_added
    ok_added = a_mapping.add_column_for_table("fl508d", "n")
    assert not ok_added


MAPP3 = """n01=lat_end
n02=lon_end
n03=area
n04=mean
n05=stddev
n06=wtf"""


def test_augment1():
    """
    Check that we can addition mappings.
    """
    # Simple case, one column extra
    dest_mapping = TableMapping(ObjectFields).load_from_equal_list(MAPP2)
    src_mapping = TableMapping(ObjectFields).load_from_equal_list(MAPP3)
    aug, transforms, errs = dest_mapping.augmented_with(src_mapping)
    # 5 in common, one in +
    assert len(aug) == 6
    assert not errs
    assert not transforms


def test_augment2():
    """
    Check that we can addition mappings.
    """
    # Simple case, one column extra
    dest_mapping = TableMapping(ObjectFields).load_from_equal_list(MAPP_DST)
    src_mapping = TableMapping(ObjectFields).load_from_equal_list(MAPP_SRC)
    aug, remap, errs = dest_mapping.augmented_with(src_mapping)
    # 5, all in common
    assert len(aug) == 5
    assert not errs
    assert remap == [
        ("n01", "n02"),
        ("n02", "n05"),
        ("n03", "n04"),
        ("n04", "n03"),
        ("n05", "n01"),
    ]


MAPP_DST2 = """n01=stddev
n02=lat_end
n03=mean
n04=area
n05=lon_end"""

MAPP_SRC2 = """n01=lat_end
n02=lon_end
n03=area
n04=nada
n07=mean
n111=wtf
n125=stddev"""


def test_augment3():
    """
    Check that we can addition mappings.
    """
    # Simple case, one column extra
    dest_mapping = TableMapping(ObjectFields).load_from_equal_list(MAPP_DST2)
    src_mapping = TableMapping(ObjectFields).load_from_equal_list(MAPP_SRC2)
    aug, remaps, errs = dest_mapping.augmented_with(src_mapping)
    # 7, wtf and nada are extra
    assert len(aug) == 7
    assert not errs
    assert remaps == [
        RemapOp(frm="n01", to="n02"),
        RemapOp(frm="n02", to="n05"),
        RemapOp(frm="n03", to="n04"),
        RemapOp(frm="n04", to="n06"),  # Newly added
        RemapOp(frm="n07", to="n03"),
        RemapOp(frm="n111", to="n07"),  # Newly added
        RemapOp(frm="n125", to="n01"),
        RemapOp(frm=None, to="n111"),
        RemapOp(frm=None, to="n125"),
    ]


MAPP_SRC3 = """
n01=lat_end             
n02=lon_end             
n03=_item               
n04=area                
n05=area_exc            
n06=_area               
n07=area_based_diameter 
n08=meangreyimage       
n09=meangreyobjet       
n10=modegreyobjet       
n11=sigmagrey           
n12=mingrey             
n13=maxgrey             
n14=sumgrey             
n15=breadth             
n16=length              
n17=elongation          
n18=perim               
n19=minferetdiam        
n20=maxferetdiam        
n21=meanferetdiam       
n22=feretelongation     
n23=compactness         
n24=intercept0          
n25=intercept45         
n26=intercept90         
n27=intercept135        
n28=convexhullarea      
n29=convexhullfillratio 
n30=convexperimeter     
n31=n_number_of_runs    
n32=n_chained_pixels    
n33=n_convex_hull_points
n34=n_number_of_holes   
n35=transparence        
n36=roughness           
n37=rectangularity      
n38=skewness            
n39=kurtosis            
n40=fractal_box         
n41=hist25              
n42=hist50              
n43=hist75              
n44=valhist25           
n45=valhist50           
n46=valhist75           
n47=nobj25              
n48=nobj50              
n49=nobj75              
n50=symetrieh           
n51=symetriev           
n52=skelarea            
n53=thick_r             
n54=cdist               
n55=bord                
n56=isduplicate         
t01=label               
t02=foundinframe        
t03=xmin                
t04=ymin                
t05=xmax                
t06=ymax                
t07=param1              
t08=param2              
t09=param3              
t10=param4              
t11=param5              
t12=tag                 
t13=bord_1              
t14=cutted20
t15=framename           
t16=annotation
"""
MAPP_DST3 = """
n01=lat_end             
n02=lon_end             
n03=_item               
n04=area                
n05=area_exc            
n06=_area               
n07=area_based_diameter 
n08=meangreyimage       
n09=meangreyobjet       
n10=modegreyobjet       
n11=sigmagrey           
n12=mingrey             
n13=maxgrey             
n14=sumgrey             
n15=breadth             
n16=length              
n17=elongation          
n18=perim               
n19=minferetdiam        
n20=maxferetdiam        
n21=meanferetdiam       
n22=feretelongation     
n23=compactness         
n24=intercept0          
n25=intercept45         
n26=intercept90         
n27=intercept135        
n28=convexhullarea      
n29=convexhullfillratio 
n30=convexperimeter     
n31=n_number_of_runs    
n32=n_chained_pixels    
n33=n_convex_hull_points
n34=n_number_of_holes   
n35=transparence        
n36=roughness           
n37=rectangularity      
n38=skewness            
n39=kurtosis            
n40=fractal_box         
n41=hist25              
n42=hist50              
n43=hist75              
n44=valhist25           
n45=valhist50           
n46=valhist75           
n47=nobj25              
n48=nobj50              
n49=nobj75              
n50=symetrieh           
n51=symetriev           
n52=skelarea            
n53=thick_r             
n54=cdist               
n55=bord                
n56=cutted20
n57=isduplicate         
t01=label               
t02=foundinframe        
t03=xmin                
t04=ymin                
t05=xmax                
t06=ymax                
t07=param1              
t08=param2              
t09=param3              
t10=param4              
t11=param5              
t12=tag                 
t13=bord_1              
t14=framename           
t15=annotation
"""


def test_augment4():
    """
    Check that we have a decent error if the remapping doesn't work for e.g. types reason.
    """
    # Simple case, one column extra
    dest_mapping = TableMapping(ObjectFields).load_from_equal_list(MAPP_DST3)
    src_mapping = TableMapping(ObjectFields).load_from_equal_list(MAPP_SRC3)
    with pytest.raises(AssertionError) as e_info:
        aug, remaps, errs = dest_mapping.augmented_with(src_mapping)
    assert (
        e_info.value.args[0]
        == "Destination column 'cutted20' aka 'n56' and source column 'cutted20' aka 't14' have different types!"
    )
