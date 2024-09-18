-- As per https://docs.google.com/spreadsheets/d/1fX514euFI2oa1u5INxjXpTSNdIVuyw3H91a0roYWT8E
update objectsclassifhisto
set classif_qual='P'
where classif_type = 'A'
  and classif_qual is NULL
  and classif_who is null
  and classif_score is not null;
update objectsclassifhisto
set classif_score = 1
where classif_type = 'A'
  and classif_qual = 'P'
  and classif_who is null
  and classif_score is null;
update objectsclassifhisto
set classif_qual='P'
where classif_type = 'A'
  and classif_qual = 'V'
  and classif_who is null;
update objectsclassifhisto
set classif_qual='P'
where classif_type = 'A'
  and classif_qual = 'D';
delete
from objectsclassifhisto
where classif_type = 'M'
  and classif_qual is null;
update objectsclassifhisto
set classif_who=1
where classif_type = 'M'
  and classif_qual = 'V'
  and classif_who is null
  and classif_score is null;
update objectsclassifhisto
set classif_who=1
where classif_type = 'M'
  and classif_qual = 'D'
  and classif_who is null
  and classif_score is null;
delete
from objectsclassifhisto
where classif_type = 'M'
  and classif_qual = 'P'
  and classif_who is null
  and classif_score is null;
update objectsclassifhisto
set classif_qual='V'
where classif_type = 'M'
  and classif_qual = 'P'
  and classif_who is not null
  and classif_score is null;
