# Common formulea for exports
uvp_formulae = {
    "subsample_coef": "1/ssm.sub_part",
    "total_water_volume": "sam.tot_vol",  # Volumes are in m3 already for this data
    "individual_volume": "4.0/3.0*math.pi*(math.sqrt(obj.area/math.pi)*ssm.pixel)**3",
}
