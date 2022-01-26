"""single parent acquisition

Revision ID: 08fdc2b6bce0
Revises: d3309bb7012e
Create Date: 2021-01-16 06:08:44.933682

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = '08fdc2b6bce0'
down_revision = 'd3309bb7012e'

# Ensure that all acquisitions have a single parent. The relationship is stored in obj_head
duplicate_acquisitions_if_needed_sql = """
begin;

create temp table notok_objects as 
select obh.objid from obj_head obh
  join acquisitions acq on acq.acquisid = obh.acquisid
 where acq.projid != obh.projid or obh.projid is null
 union all 
select obh.objid from obj_head obh
  join samples sam on sam.sampleid = obh.sampleid
 where sam.projid != obh.projid or obh.projid is null;
 
delete from images where objid in (select * from notok_objects);

delete from obj_head where objid in (select * from notok_objects);
    
-- Initial state of relations
drop table if exists acq2sam;
create temp table acq2sam as 
select distinct obh.sampleid, obh.acquisid, obh.projid 
  from obj_head obh;

-- Need to duplicate the acquisitions attached to several samples
drop table if exists acqs2duplicate;
create temp table acqs2duplicate as
select acq.acquisid, acq.orig_id as acq_orig_id
  from acq2sam a2s
  join acquisitions acq on acq.acquisid = a2s.acquisid
  join samples sam on sam.sampleid = a2s.sampleid
 group by acq.acquisid    
having count(sam.sampleid) > 1;

-- The relations to transform
drop table if exists rels2fork;
create temp table rels2fork as
select acq.acquisid, null::integer as acquisid_to, sam.sampleid
  from acquisitions acq
  join acqs2duplicate a2d on a2d.acquisid = acq.acquisid 
  join acq2sam a2s on a2s.acquisid = acq.acquisid 
  join samples sam on sam.sampleid = a2s.sampleid;
create index rels2fork$as on rels2fork(acquisid, sampleid);

-- Give IDs for all new acquisitions, i.e. all but the 'original' one
update rels2fork r2f
   set acquisid_to = nextval('seq_acquisitions')
 where r2f.sampleid != (select min(sampleid) 
                          from rels2fork r2fs 
                         where r2fs.acquisid=r2f.acquisid);

-- Duplicate acquisitions as many times as needed
insert into acquisitions (acquisid, projid, 
                          orig_id,
                          instrument,
                          t01, t02, t03, t04, t05, t06, t07, t08, t09, t10, 
                          t11, t12, t13, t14, t15, t16, t17, t18, t19, t20, 
                          t21, t22, t23, t24, t25, t26, t27, t28, t29, t30)
select r2f.acquisid_to, acq.projid,
       acq.orig_id || '@' || sam.orig_id, 
       acq.instrument,
       acq.t01, acq.t02, acq.t03, acq.t04, acq.t05, acq.t06, acq.t07, acq.t08, acq.t09, acq.t10, 
       acq.t11, acq.t12, acq.t13, acq.t14, acq.t15, acq.t16, acq.t17, acq.t18, acq.t19, acq.t20, 
       acq.t21, acq.t22, acq.t23, acq.t24, acq.t25, acq.t26, acq.t27, acq.t28, acq.t29, acq.t30
  from acquisitions acq
  join rels2fork r2f on r2f.acquisid = acq.acquisid and r2f.acquisid_to is not null
  join samples sam on sam.sampleid = r2f.sampleid;  

-- Mark the original as well
update acquisitions acq
   set orig_id = acq.orig_id || '@' || sam.orig_id
  from rels2fork r2f 
  join samples sam on sam.sampleid = r2f.sampleid  
 where r2f.acquisid = acq.acquisid and r2f.acquisid_to is null;
  
-- Duplicate processes as there is a 1<->1 relationship b/w acquisitions and process
insert into process (processid, projid, orig_id, 
                     t01, t02, t03, t04, t05, t06, t07, t08, t09, t10, 
                     t11, t12, t13, t14, t15, t16, t17, t18, t19, t20, 
                     t21, t22, t23, t24, t25, t26, t27, t28, t29, t30)
select r2f.acquisid_to, prc.projid, 
       prc.orig_id || '@' || sam.orig_id, 
       prc.t01, prc.t02, prc.t03, prc.t04, prc.t05, prc.t06, prc.t07, prc.t08, prc.t09, prc.t10, 
       prc.t11, prc.t12, prc.t13, prc.t14, prc.t15, prc.t16, prc.t17, prc.t18, prc.t19, prc.t20, 
       prc.t21, prc.t22, prc.t23, prc.t24, prc.t25, prc.t26, prc.t27, prc.t28, prc.t29, prc.t30
  from process prc
  join rels2fork r2f on r2f.acquisid = prc.processid and r2f.acquisid_to is not null
  join samples sam on sam.sampleid = r2f.sampleid;

-- Mark original process as well
update process prc
   set orig_id = prc.orig_id || '@' || sam.orig_id
  from rels2fork r2f 
  join samples sam on sam.sampleid = r2f.sampleid  
 where r2f.acquisid = prc.processid and r2f.acquisid_to is null;

-- Speed up update by removing checks during update
DROP INDEX is_objectsacquisition;

ALTER TABLE obj_head DROP CONSTRAINT obj_head_acquisid_fkey;

-- Make objects point to new acquisitions+process pairs
update obj_head obh
   set acquisid=r2f.acquisid_to
  from rels2fork r2f
 where r2f.acquisid_to is not null
   and obh.acquisid = r2f.acquisid
   and obh.sampleid = r2f.sampleid;

-- Re-create checks
CREATE INDEX is_objectsacquisition
    ON obj_head USING btree
    (acquisid ASC NULLS LAST)
    TABLESPACE pg_default;

ALTER TABLE obj_head
    CLUSTER ON is_objectsacquisition;

ALTER TABLE obj_head
    ADD CONSTRAINT obj_head_acquisid_fkey FOREIGN KEY (acquisid)
    REFERENCES acquisitions (acquisid) MATCH SIMPLE
    ON UPDATE NO ACTION
    ON DELETE CASCADE;

COMMIT;
"""

ref_sample_from_acquisition = """
begin;

create temp table obj_path 
    as select projid, sampleid, acquisid, count(objid) as cnt 
  from obj_head 
 group by projid, sampleid, acquisid;

create index obj_path$acq on obj_path(acquisid) include (sampleid, projid);

ALTER TABLE acquisitions ADD COLUMN acq_sample_id INTEGER;

-- Get rid of empty acquisitions as we don't know their parent - 14 of them in production DB
delete from acquisitions
 where acquisid not in (select acquisid from obj_path);
 
-- Link acquisitions to their parent
update acquisitions acq 
   set acq_sample_id = (select sampleid 
                          from obj_path obp 
                         where obp.acquisid = acq.acquisid);

-- Add constraints that we had to exclude during creation
ALTER TABLE acquisitions ALTER COLUMN acq_sample_id SET NOT NULL;

ALTER TABLE acquisitions
    ADD CONSTRAINT acquisitions_sampleid_fkey FOREIGN KEY (acq_sample_id)
    REFERENCES samples (sampleid) MATCH SIMPLE
    ON UPDATE NO ACTION
    ON DELETE NO ACTION;
    
COMMIT;
"""


def upgrade():
    op.execute(duplicate_acquisitions_if_needed_sql)
    # ### commands auto generated by Alembic - please adjust! ###
    # Below doesn't work when the table has rows
    # op.add_column('acquisitions', sa.Column('acq_sample_id', sa.INTEGER(), nullable=False))
    # op.create_foreign_key(None, 'acquisitions', 'samples', ['acq_sample_id'], ['sampleid'])
    op.execute(ref_sample_from_acquisition)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('acquisitions', 'acq_sample_id')
    # ### end Alembic commands ###
