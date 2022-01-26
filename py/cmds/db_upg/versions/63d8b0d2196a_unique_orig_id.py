"""unique orig_id

Revision ID: 63d8b0d2196a
Revises: cee3a33476db
Create Date: 2020-12-02 18:07:55.405910

"""

# revision identifiers, used by Alembic.
revision = '63d8b0d2196a'
down_revision = 'cee3a33476db'

from alembic import op

# Merge duplicate samples in each project
merge_samples = """
begin;
create temp table sample_remap
as select sam.sampleid as dst_id, array_agg(sam2.sampleid) as src_id from samples sam
 join samples sam2 on sam2.sampleid > sam.sampleid
                   and sam2.orig_id = sam.orig_id
                   and sam2.projid = sam.projid
                   -- (re) computed columns
                   -- and (sam2.latitude = sam.latitude or (sam2.latitude is null and sam.latitude is null))
                   -- and (sam2.longitude = sam.longitude or (sam2.longitude is null and sam.longitude is null))
                   and (sam2.dataportal_descriptor = sam.dataportal_descriptor or 
                   (sam2.dataportal_descriptor is null and sam.dataportal_descriptor is null))
                   and (sam2.t01 = sam.t01 or (sam2.t01 is null and sam.t01 is null))
                   and (sam2.t02 = sam.t02 or (sam2.t02 is null and sam.t02 is null))
                   and (sam2.t03 = sam.t03 or (sam2.t03 is null and sam.t03 is null))
                   and (sam2.t04 = sam.t04 or (sam2.t04 is null and sam.t04 is null))
                   and (sam2.t05 = sam.t05 or (sam2.t05 is null and sam.t05 is null))
                   and (sam2.t06 = sam.t06 or (sam2.t06 is null and sam.t06 is null))
                   and (sam2.t07 = sam.t07 or (sam2.t07 is null and sam.t07 is null))
                   and (sam2.t08 = sam.t08 or (sam2.t08 is null and sam.t08 is null))
                   and (sam2.t09 = sam.t09 or (sam2.t09 is null and sam.t09 is null))
                   and (sam2.t10 = sam.t10 or (sam2.t10 is null and sam.t10 is null))
                   and (sam2.t11 = sam.t11 or (sam2.t11 is null and sam.t11 is null))
                   and (sam2.t12 = sam.t12 or (sam2.t12 is null and sam.t12 is null))
                   and (sam2.t13 = sam.t13 or (sam2.t13 is null and sam.t13 is null))
                   and (sam2.t14 = sam.t14 or (sam2.t14 is null and sam.t14 is null))
                   and (sam2.t15 = sam.t15 or (sam2.t15 is null and sam.t15 is null))
                   and (sam2.t16 = sam.t16 or (sam2.t16 is null and sam.t16 is null))
                   and (sam2.t17 = sam.t17 or (sam2.t17 is null and sam.t17 is null))
                   and (sam2.t18 = sam.t18 or (sam2.t18 is null and sam.t18 is null))
                   and (sam2.t19 = sam.t19 or (sam2.t19 is null and sam.t19 is null))
                   and (sam2.t20 = sam.t20 or (sam2.t20 is null and sam.t20 is null))
                   and (sam2.t21 = sam.t21 or (sam2.t21 is null and sam.t21 is null))
                   and (sam2.t22 = sam.t22 or (sam2.t22 is null and sam.t22 is null))
                   and (sam2.t23 = sam.t23 or (sam2.t23 is null and sam.t23 is null))
                   and (sam2.t24 = sam.t24 or (sam2.t24 is null and sam.t24 is null))
                   and (sam2.t25 = sam.t25 or (sam2.t25 is null and sam.t25 is null))
                   and (sam2.t26 = sam.t26 or (sam2.t26 is null and sam.t26 is null))
                   and (sam2.t27 = sam.t27 or (sam2.t27 is null and sam.t27 is null))
                   and (sam2.t28 = sam.t28 or (sam2.t28 is null and sam.t28 is null))
                   and (sam2.t29 = sam.t29 or (sam2.t29 is null and sam.t29 is null))
                   and (sam2.t30 = sam.t30 or (sam2.t30 is null and sam.t30 is null))
group by sam.sampleid;

update obj_head set sampleid = dst_id
  from sample_remap rmp
 where sampleid = any(src_id);

delete from samples
 using sample_remap rmp
 where sampleid = any(rmp.src_id);
commit
"""

# Merge duplicate acquisitions (same all except id) in each project
merge_acquisitions = """
begin;
create temp table acquis_remap
as 
select acq.acquisid as dst_id, array_agg(acq2.acquisid) as src_id from acquisitions acq
 join acquisitions acq2 on acq2.acquisid > acq.acquisid
                   and acq2.projid = acq.projid
                   and acq2.orig_id = acq.orig_id
                   and (acq2.instrument = acq.instrument or (acq2.instrument is null and acq.instrument is null))
                   and (acq2.t01 = acq.t01 or (acq2.t01 is null and acq.t01 is null))
                   and (acq2.t02 = acq.t02 or (acq2.t02 is null and acq.t02 is null))
                   and (acq2.t03 = acq.t03 or (acq2.t03 is null and acq.t03 is null))
                   and (acq2.t04 = acq.t04 or (acq2.t04 is null and acq.t04 is null))
                   and (acq2.t05 = acq.t05 or (acq2.t05 is null and acq.t05 is null))
                   and (acq2.t06 = acq.t06 or (acq2.t06 is null and acq.t06 is null))
                   and (acq2.t07 = acq.t07 or (acq2.t07 is null and acq.t07 is null))
                   and (acq2.t08 = acq.t08 or (acq2.t08 is null and acq.t08 is null))
                   and (acq2.t09 = acq.t09 or (acq2.t09 is null and acq.t09 is null))
                   and (acq2.t10 = acq.t10 or (acq2.t10 is null and acq.t10 is null))
                   and (acq2.t11 = acq.t11 or (acq2.t11 is null and acq.t11 is null))
                   and (acq2.t12 = acq.t12 or (acq2.t12 is null and acq.t12 is null))
                   and (acq2.t13 = acq.t13 or (acq2.t13 is null and acq.t13 is null))
                   and (acq2.t14 = acq.t14 or (acq2.t14 is null and acq.t14 is null))
                   and (acq2.t15 = acq.t15 or (acq2.t15 is null and acq.t15 is null))
                   and (acq2.t16 = acq.t16 or (acq2.t16 is null and acq.t16 is null))
                   and (acq2.t17 = acq.t17 or (acq2.t17 is null and acq.t17 is null))
                   and (acq2.t18 = acq.t18 or (acq2.t18 is null and acq.t18 is null))
                   and (acq2.t19 = acq.t19 or (acq2.t19 is null and acq.t19 is null))
                   and (acq2.t20 = acq.t20 or (acq2.t20 is null and acq.t20 is null))
                   and (acq2.t21 = acq.t21 or (acq2.t21 is null and acq.t21 is null))
                   and (acq2.t22 = acq.t22 or (acq2.t22 is null and acq.t22 is null))
                   and (acq2.t23 = acq.t23 or (acq2.t23 is null and acq.t23 is null))
                   and (acq2.t24 = acq.t24 or (acq2.t24 is null and acq.t24 is null))
                   and (acq2.t25 = acq.t25 or (acq2.t25 is null and acq.t25 is null))
                   and (acq2.t26 = acq.t26 or (acq2.t26 is null and acq.t26 is null))
                   and (acq2.t27 = acq.t27 or (acq2.t27 is null and acq.t27 is null))
                   and (acq2.t28 = acq.t28 or (acq2.t28 is null and acq.t28 is null))
                   and (acq2.t29 = acq.t29 or (acq2.t29 is null and acq.t29 is null))
                   and (acq2.t30 = acq.t30 or (acq2.t30 is null and acq.t30 is null))
group by acq.acquisid;

update obj_head set acquisid = dst_id
  from acquis_remap rmp
 where acquisid = any(src_id);

delete from acquisitions
 using acquis_remap rmp
 where acquisid = any(rmp.src_id);
commit
"""

# Merge duplicate process (same all except id) in each project
merge_processes = """
begin;
create temp table process_remap
as select prc.processid as dst_id, array_agg(prc2.processid) as src_id from process prc
 join process prc2 on prc2.processid > prc.processid
                   and prc2.projid = prc.projid
                   and prc2.orig_id = prc.orig_id
                   and (prc2.t01 = prc.t01 or (prc2.t01 is null and prc.t01 is null))
                   and (prc2.t02 = prc.t02 or (prc2.t02 is null and prc.t02 is null))
                   and (prc2.t03 = prc.t03 or (prc2.t03 is null and prc.t03 is null))
                   and (prc2.t04 = prc.t04 or (prc2.t04 is null and prc.t04 is null))
                   and (prc2.t05 = prc.t05 or (prc2.t05 is null and prc.t05 is null))
                   and (prc2.t06 = prc.t06 or (prc2.t06 is null and prc.t06 is null))
                   and (prc2.t07 = prc.t07 or (prc2.t07 is null and prc.t07 is null))
                   and (prc2.t08 = prc.t08 or (prc2.t08 is null and prc.t08 is null))
                   and (prc2.t09 = prc.t09 or (prc2.t09 is null and prc.t09 is null))
                   and (prc2.t10 = prc.t10 or (prc2.t10 is null and prc.t10 is null))
                   and (prc2.t11 = prc.t11 or (prc2.t11 is null and prc.t11 is null))
                   and (prc2.t12 = prc.t12 or (prc2.t12 is null and prc.t12 is null))
                   and (prc2.t13 = prc.t13 or (prc2.t13 is null and prc.t13 is null))
                   and (prc2.t14 = prc.t14 or (prc2.t14 is null and prc.t14 is null))
                   and (prc2.t15 = prc.t15 or (prc2.t15 is null and prc.t15 is null))
                   and (prc2.t16 = prc.t16 or (prc2.t16 is null and prc.t16 is null))
                   and (prc2.t17 = prc.t17 or (prc2.t17 is null and prc.t17 is null))
                   and (prc2.t18 = prc.t18 or (prc2.t18 is null and prc.t18 is null))
                   and (prc2.t19 = prc.t19 or (prc2.t19 is null and prc.t19 is null))
                   and (prc2.t20 = prc.t20 or (prc2.t20 is null and prc.t20 is null))
                   and (prc2.t21 = prc.t21 or (prc2.t21 is null and prc.t21 is null))
                   and (prc2.t22 = prc.t22 or (prc2.t22 is null and prc.t22 is null))
                   and (prc2.t23 = prc.t23 or (prc2.t23 is null and prc.t23 is null))
                   and (prc2.t24 = prc.t24 or (prc2.t24 is null and prc.t24 is null))
                   and (prc2.t25 = prc.t25 or (prc2.t25 is null and prc.t25 is null))
                   and (prc2.t26 = prc.t26 or (prc2.t26 is null and prc.t26 is null))
                   and (prc2.t27 = prc.t27 or (prc2.t27 is null and prc.t27 is null))
                   and (prc2.t28 = prc.t28 or (prc2.t28 is null and prc.t28 is null))
                   and (prc2.t29 = prc.t29 or (prc2.t29 is null and prc.t29 is null))
                   and (prc2.t30 = prc.t30 or (prc2.t30 is null and prc.t30 is null))
group by prc.processid;

update obj_head set processid = dst_id
  from process_remap rmp
 where processid = any(src_id);

delete from process
 using process_remap rmp
 where processid = any(rmp.src_id);
commit
"""

# Build a new orig_id where needed, i.e. when the same orig_id is used in other samples of same project
# The orig_ids are generated considering that other parents are newer "versions" of the first one, so
# we add a suffix like _:1, _:2, ...
unq_orig_ids = """
begin;
update samples sam
   set orig_id = orig_id || '_:' || (select count(1) from samples sam2 
                                      where sam2.projid = sam.projid
                                        and sam2.orig_id = sam.orig_id
                                        and sam2.sampleid < sam.sampleid)
 where exists (select 1 from samples sam2
               where sam2.projid = sam.projid
                 and sam2.orig_id = sam.orig_id 
                 and sam2.sampleid < sam.sampleid );

update acquisitions acq
   set orig_id = orig_id || '_:' || (select count(1) from acquisitions acq2 
                                      where acq2.projid = acq.projid
                                        and acq2.orig_id = acq.orig_id
                                        and acq2.acquisid < acq.acquisid)
 where exists (select 1 from acquisitions acq2
               where acq2.projid = acq.projid
                 and acq2.orig_id = acq.orig_id 
                 and acq2.acquisid < acq.acquisid);               
commit
"""


def upgrade():
    op.execute(merge_samples)
    op.execute(merge_acquisitions)
    op.execute(merge_processes)
    op.execute(unq_orig_ids.replace(':', '\:'))
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_index('IS_AcquisitionsProjectOrigId', 'acquisitions', ['projid', 'orig_id'], unique=True)
    op.drop_index('IS_AcquisitionsProject', table_name='acquisitions')
    op.create_index('IS_SamplesProjectOrigId', 'samples', ['projid', 'orig_id'], unique=True)
    op.drop_index('IS_SamplesProject', table_name='samples')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_index('IS_SamplesProject', 'samples', ['projid'], unique=False)
    op.drop_index('IS_SamplesProjectOrigId', table_name='samples')
    op.create_index('IS_AcquisitionsProject', 'acquisitions', ['projid'], unique=False)
    op.drop_index('IS_AcquisitionsProjectOrigId', table_name='acquisitions')
    # ### end Alembic commands ###
