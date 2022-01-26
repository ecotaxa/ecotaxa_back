"""acquis one to one process

Revision ID: d3309bb7012e
Revises: 63d8b0d2196a
Create Date: 2020-12-04 10:18:42.738183

"""

# revision identifiers, used by Alembic.
revision = 'd3309bb7012e'
down_revision = '63d8b0d2196a'

import sqlalchemy as sa
from alembic import op

# Remove unreferenced process & acquisitions as we need a 1<->1 relationship
cleanup_sql = """
begin;
delete from acquisitions
where acquisid in (
    select acquisid from acquisitions
    except
    select acquisid from obj_head
);

delete from process
where processid in (
    select processid from process
    except
    select processid from obj_head
);
commit
"""

one_to_one_sql = """
begin;
create table tmp_acq_proc
as select distinct acquisid, processid, null::integer as acquisid_to, null::integer as processid_to from obj_head;
create unique index tmp_acq_proc$ap on tmp_acq_proc(acquisid, processid);
create unique index tmp_acq_proc$pa on tmp_acq_proc(processid, acquisid);

-- Create one new process per _extra_ acquisition in group
with procs_with_several_acqs as (select processid, min(acquisid) as min_acquisid 
                                   from tmp_acq_proc 
                                  group by processid 
                                 having count(1) > 1)
update tmp_acq_proc tap
   set processid_to = nextval('seq_process')
  from procs_with_several_acqs pwsa
 where tap.processid = pwsa.processid
   and tap.acquisid > pwsa.min_acquisid;

insert into process (processid, projid, orig_id, 
                     t01, t02, t03, t04, t05, t06, t07, t08, t09, t10, 
                     t11, t12, t13, t14, t15, t16, t17, t18, t19, t20, 
                     t21, t22, t23, t24, t25, t26, t27, t28, t29, t30)
select tap.processid_to, prc.projid, prc.orig_id, 
       prc.t01, prc.t02, prc.t03, prc.t04, prc.t05, prc.t06, prc.t07, prc.t08, prc.t09, prc.t10, 
       prc.t11, prc.t12, prc.t13, prc.t14, prc.t15, prc.t16, prc.t17, prc.t18, prc.t19, prc.t20, 
       prc.t21, prc.t22, prc.t23, prc.t24, prc.t25, prc.t26, prc.t27, prc.t28, prc.t29, prc.t30
  from process prc
  join tmp_acq_proc tap on tap.processid = prc.processid and tap.processid_to is not null;

with procs_to_remap as (select acquisid, processid, processid_to
                                                  from tmp_acq_proc 
                                                 where processid_to is not null)
update obj_head obh
   set processid=rmp.processid_to
  from procs_to_remap rmp
 where obh.acquisid = rmp.acquisid
   and obh.processid = rmp.processid;

-- Create one new acquisition per _extra_ process in group
with acqs_with_several_procs as (select acquisid, min(processid) as min_processid 
                                   from tmp_acq_proc 
                                  group by acquisid 
                                 having count(1) > 1)
update tmp_acq_proc tap
   set acquisid_to = nextval('seq_acquisitions')
  from acqs_with_several_procs awsp
 where tap.acquisid = awsp.acquisid 
   and tap.processid > awsp.min_processid;

insert into acquisitions (acquisid, projid, 
                          orig_id,
                          instrument,
                          t01, t02, t03, t04, t05, t06, t07, t08, t09, t10, 
                          t11, t12, t13, t14, t15, t16, t17, t18, t19, t20, 
                          t21, t22, t23, t24, t25, t26, t27, t28, t29, t30)
select tap.acquisid_to, acq.projid,
       acq.orig_id || '_:' || (select count(1) from tmp_acq_proc tap2 
                                where tap2.acquisid = tap.acquisid
                                  and tap2.processid < tap.processid), 
       acq.instrument,
       acq.t01, acq.t02, acq.t03, acq.t04, acq.t05, acq.t06, acq.t07, acq.t08, acq.t09, acq.t10, 
       acq.t11, acq.t12, acq.t13, acq.t14, acq.t15, acq.t16, acq.t17, acq.t18, acq.t19, acq.t20, 
       acq.t21, acq.t22, acq.t23, acq.t24, acq.t25, acq.t26, acq.t27, acq.t28, acq.t29, acq.t30
  from acquisitions acq
  join tmp_acq_proc tap on tap.acquisid = acq.acquisid and tap.acquisid_to is not null;

-- Apply the change to objects where needed
with acqs_to_remap as (select acquisid, processid, acquisid_to
                         from tmp_acq_proc 
                        where acquisid_to is not null)
update obj_head obh
   set acquisid=rmp.acquisid_to
  from acqs_to_remap rmp
 where obh.acquisid = rmp.acquisid
   and obh.processid = rmp.processid;

commit
"""

acquis_process_same_id = """
begin;
ALTER TABLE process DROP CONSTRAINT process_pkey;

-- Just in case, warp IDs to negative, if any remapping fails it will remain as such
update process prc set processid = -processid;
   
-- copy IDs from acquisitions to corresponding (now unique) process
update process prc
   set processid = coalesce(tap.acquisid_to, tap.acquisid)
  from tmp_acq_proc tap
 where prc.processid = -coalesce(tap.processid_to, tap.processid);

ALTER TABLE process ADD CONSTRAINT process_pkey PRIMARY KEY (processid);

commit
"""

def upgrade():
    op.execute(cleanup_sql)
    op.execute(one_to_one_sql)
    op.execute('drop view objects')
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index('is_objectsprocess', table_name='obj_head')
    op.drop_constraint('obj_head_processid_fkey', 'obj_head', type_='foreignkey')
    op.drop_column('obj_head', 'processid')
    # ### end Alembic commands ###
    op.execute(acquis_process_same_id)
    op.execute("""create view objects as 
                  select oh.*, oh.acquisid as processid, ofi.*
                    from obj_head oh 
                    join obj_field ofi on oh.objid=ofi.objfid""")


def downgrade():
    # LS: Untested, so most probably incomplete.
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('obj_head', sa.Column('processid', sa.INTEGER(), autoincrement=False, nullable=False))
    op.create_foreign_key('obj_head_processid_fkey', 'obj_head', 'process', ['processid'], ['processid'])
    op.create_index('is_objectsprocess', 'obj_head', ['processid'], unique=False)
    # ### end Alembic commands ###
