import os
from io import BytesIO, TextIOWrapper
from zipfile import ZipFile

from tests.credentials import ADMIN_AUTH
from tests.test_import import SHARED_DIR


def download_and_unzip_and_check(fastapi, job_id, ref_dir, only_hdr: bool = False):
    dl_url = JOB_DOWNLOAD_URL.format(job_id=job_id)
    rsp = fastapi.get(dl_url, headers=ADMIN_AUTH)
    unzip_and_check(rsp.content, ref_dir, only_hdr)


def recursive_list_dir(pth: str):
    dir_list = [pth]
    files = []
    while len(dir_list) > 0:
        for (dirpath, dirnames, filenames) in os.walk(dir_list.pop()):
            dirpath = dirpath[len(pth) + 1:]
            dir_list.extend(dirnames)
            files.extend(map(lambda n: os.path.join(*n),
                             zip([dirpath] * len(filenames),
                                 filenames)))
    return files


def unzip_and_check(zip_content, ref_dir: str, only_hdr: bool):
    ref_dir_path = SHARED_DIR / EXPORT_ROOT_REF_DIR / ref_dir
    ref_dir_content = recursive_list_dir(str(ref_dir_path))

    pseudo_file = BytesIO(zip_content)
    zip_file = ZipFile(pseudo_file)
    for a_file in zip_file.filelist:
        name = a_file.filename
        if name.endswith(".log"):
            continue
        assert name in ref_dir_content
        ref_dir_content.remove(name)
        with zip_file.open(name) as myfile:
            content_bin = myfile.read()
        if name.endswith(".tsv"):
            one_tsv_check(content_bin, name, only_hdr, ref_dir_path)
    assert len(ref_dir_content) == 0


def one_tsv_check(content_bin, name, only_hdr, ref_dir_path):
    file_content = TextIOWrapper(BytesIO(content_bin), "utf-8-sig").readlines()
    print("".join(file_content))
    ref_content = open(ref_dir_path / name).readlines()
    assert len(file_content) == len(ref_content), "For %s, not same number of lines" % ref_dir_path
    num_line = 1
    for act, ref in zip(file_content, ref_content):
        assert act == ref, "diff A'%s'E'%s' in %s/%s line %d" % (act, ref, ref_dir_path, name, num_line)
        if only_hdr:
            break
        num_line += 1


EXPORT_ROOT_REF_DIR = "ref_exports"
JOB_DOWNLOAD_URL = "/jobs/{job_id}/file"
JOB_LOG_DOWNLOAD_URL = "/jobs/{job_id}/log"


def download_and_check(fastapi, job_id, ref_dir, only_hdr: bool = False):
    dl_url = JOB_DOWNLOAD_URL.format(job_id=job_id)
    rsp = fastapi.get(dl_url, headers=ADMIN_AUTH)
    tsv_check(rsp.content, ref_dir, only_hdr)


def get_log_file(fastapi, job_id):
    log_url = JOB_LOG_DOWNLOAD_URL.format(job_id=job_id)
    rsp = fastapi.get(log_url, headers=ADMIN_AUTH)
    return rsp.content


def tsv_check(tsv_content, ref_dir: str, only_hdr: bool):
    ref_dir_path = SHARED_DIR / EXPORT_ROOT_REF_DIR / ref_dir
    one_tsv_check(tsv_content, "ref.tsv", only_hdr=False, ref_dir_path=ref_dir_path)
