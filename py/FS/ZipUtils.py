# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2026  Picheral, Colin, Irisson (UPMC-CNRS)
#
# ZIP parsing helpers, from the PKWARE APPNOTE. Only what is needed to walk the
# central directory without loading members: EOCD, ZIP64 EOCD, and CD entries.
#
import os
import struct
import zipfile
import zlib
from pathlib import Path
from typing import BinaryIO, Generator, Optional, Tuple

import stream_unzip

from helpers.CustomException import UnprocessableEntityException
from helpers.httpexception import DETAIL_ARCHIVE_MEMBER_REFUSED

ZIP_EOCD_SIGNATURE = b"PK\x05\x06"
ZIP_EOCD_SIZE = 22
ZIP_MAX_COMMENT = 0xFFFF
ZIP64_EOCD_LOCATOR_SIGNATURE = b"PK\x06\x07"
ZIP64_EOCD_LOCATOR_SIZE = 20
ZIP64_EOCD_SIGNATURE = b"PK\x06\x06"
ZIP64_EOCD_MIN_SIZE = 56
ZIP_CD_SIGNATURE = b"PK\x01\x02"
ZIP_CD_SIZE = 46
ZIP_CD_STRUCT = struct.Struct("<4s4B4HL2L5H2L")
ZIP_UTF8_FLAG = 1 << 11
ZIP64_EXTRA_ID = 0x0001
ZIP_UNICODE_PATH_EXTRA_ID = 0x7075
ZIP_SENTINEL_32 = 0xFFFFFFFF


def get_file_size(fp: BinaryIO) -> int:
    fp.seek(0, os.SEEK_END)
    return fp.tell()


def _central_directory(fp: BinaryIO) -> Tuple[int, int, int]:
    """
    Return the absolute offset and size of the central directory, plus the base
    concatenation offset, from the End Of Central Directory record and, when
    present, its ZIP64 version.
    """
    size = get_file_size(fp)
    tail_size = min(size, ZIP_EOCD_SIZE + ZIP_MAX_COMMENT)
    fp.seek(size - tail_size)
    tail = fp.read(tail_size)
    eocd_at = tail.rfind(ZIP_EOCD_SIGNATURE)
    if eocd_at < 0:
        raise zipfile.BadZipFile("File is not a zip file")
    if len(tail) - eocd_at < ZIP_EOCD_SIZE:
        raise zipfile.BadZipFile("Truncated end of central directory")
    (
        disk_number,
        cd_disk,
        entries_this_disk,
        entries_total,
        cd_size,
        cd_offset,
        comment_size,
    ) = struct.unpack_from("<4H2LH", tail, eocd_at + 4)
    if comment_size > len(tail) - eocd_at - ZIP_EOCD_SIZE:
        raise zipfile.BadZipFile("Truncated archive comment")
    if disk_number not in (0, 0xFFFF) or cd_disk not in (0, 0xFFFF):
        raise zipfile.BadZipFile("Multi-disk zip files are not supported")
    eocd_offset = size - tail_size + eocd_at
    # A ZIP64 record may be present even when the classic fields fit in 32 bits,
    # so look for its locator rather than trusting the sentinels only.
    zip64 = (
        disk_number == 0xFFFF
        or cd_disk == 0xFFFF
        or entries_this_disk == 0xFFFF
        or entries_total == 0xFFFF
        or cd_size == ZIP_SENTINEL_32
        or cd_offset == ZIP_SENTINEL_32
    )
    locator_offset = eocd_offset - ZIP64_EOCD_LOCATOR_SIZE
    if not zip64 and locator_offset >= 0:
        fp.seek(locator_offset)
        zip64 = fp.read(4) == ZIP64_EOCD_LOCATOR_SIGNATURE
    if zip64:
        cd_size, cd_offset, location = zip64_central_directory(fp, eocd_offset, size)
    else:
        location = eocd_offset
    # "concat" is zero unless the zip was concatenated to another file.
    concat = location - cd_size - cd_offset
    start = cd_offset + concat
    if start < 0 or start + cd_size > size:
        raise zipfile.BadZipFile("Bad offset for central directory")
    return start, cd_size, concat


def central_directory(fp: BinaryIO) -> Tuple[int, int]:
    """
    Return the absolute offset and size of the central directory, from the
    End Of Central Directory record and, when present, its ZIP64 version.
    """
    start, cd_size, _ = _central_directory(fp)
    return start, cd_size


def zip64_central_directory(
    fp: BinaryIO, eocd_offset: int, size: int
) -> Tuple[int, int, int]:
    """
    Return the central directory size, its offset, and the absolute offset of
    the ZIP64 End Of Central Directory record.
    """
    locator_offset = eocd_offset - ZIP64_EOCD_LOCATOR_SIZE
    if locator_offset < 0:
        raise zipfile.BadZipFile("ZIP64 end of central directory locator missing")
    fp.seek(locator_offset)
    locator = fp.read(ZIP64_EOCD_LOCATOR_SIZE)
    if (
        len(locator) != ZIP64_EOCD_LOCATOR_SIZE
        or locator[:4] != ZIP64_EOCD_LOCATOR_SIGNATURE
    ):
        raise zipfile.BadZipFile("ZIP64 end of central directory locator missing")
    locator_disk, record_offset, disks = struct.unpack_from("<LQL", locator, 4)
    if locator_disk != 0 or disks > 1:
        raise zipfile.BadZipFile("Multi-disk zip files are not supported")
    # The record offset is relative to the archive start. With prepended data it
    # points before the actual record. The record then sits just before the
    # locator, assuming no extensible data sector.
    for candidate in (
        record_offset,
        locator_offset - ZIP64_EOCD_MIN_SIZE,
    ):
        if candidate < 0 or candidate + ZIP64_EOCD_MIN_SIZE > size:
            continue
        fp.seek(candidate)
        record = fp.read(ZIP64_EOCD_MIN_SIZE)
        if len(record) != ZIP64_EOCD_MIN_SIZE or record[:4] != ZIP64_EOCD_SIGNATURE:
            continue
        record_size = struct.unpack_from("<Q", record, 4)[0]
        if record_size < ZIP64_EOCD_MIN_SIZE - 12:
            raise zipfile.BadZipFile("Corrupt ZIP64 end of central directory")
        if record_size > size - candidate - 12:
            raise zipfile.BadZipFile("Truncated ZIP64 end of central directory")
        record_disk, record_cd_disk = struct.unpack_from("<LL", record, 16)
        if record_disk != 0 or record_cd_disk != 0:
            raise zipfile.BadZipFile("Multi-disk zip files are not supported")
        cd_size, cd_offset = struct.unpack_from("<QQ", record, 40)
        # The locator offset is relative to the archive start too, so it must
        # line up with the central directory it describes.
        if record_offset != cd_offset + cd_size:
            raise zipfile.BadZipFile("Corrupt ZIP64 end of central directory record")
        return cd_size, cd_offset, candidate
    raise zipfile.BadZipFile("ZIP64 end of central directory record missing")


def _zip64_value(data: bytes, pos: int) -> Tuple[int, int]:
    if pos + 8 > len(data):
        raise zipfile.BadZipFile("Corrupt ZIP64 extra field")
    return struct.unpack_from("<Q", data, pos)[0], pos + 8


def zip64_entry_sizes(
    extra: bytes,
    uncompressed_size: int,
    compressed_size: int,
    local_header_offset: int,
) -> Tuple[int, int, int]:
    """
    Resolve the sizes and offset stored in the ZIP64 extra field, i.e. the ones
    whose central directory value is the 32-bit sentinel.
    """
    pos = 0
    while pos + 4 <= len(extra):
        extra_id, extra_len = struct.unpack_from("<HH", extra, pos)
        pos += 4
        if pos + extra_len > len(extra):
            raise zipfile.BadZipFile("Corrupt extra field")
        if extra_id == ZIP64_EXTRA_ID:
            data = extra[pos : pos + extra_len]
            data_pos = 0
            if uncompressed_size == ZIP_SENTINEL_32:
                uncompressed_size, data_pos = _zip64_value(data, data_pos)
            if compressed_size == ZIP_SENTINEL_32:
                compressed_size, data_pos = _zip64_value(data, data_pos)
            if local_header_offset == ZIP_SENTINEL_32:
                local_header_offset, data_pos = _zip64_value(data, data_pos)
        pos += extra_len
    if (
        uncompressed_size == ZIP_SENTINEL_32
        or compressed_size == ZIP_SENTINEL_32
        or local_header_offset == ZIP_SENTINEL_32
    ):
        raise zipfile.BadZipFile("Corrupt ZIP64 extra field")
    return uncompressed_size, compressed_size, local_header_offset


def unicode_path_name(extra: bytes, raw_name: bytes) -> Optional[str]:
    """
    Return the name stored in the Unicode Path extra field (0x7075), when it is
    present and matches the raw name, as some tools write UTF-8 names there.
    """
    name_crc = zlib.crc32(raw_name)
    pos = 0
    while pos + 4 <= len(extra):
        extra_id, extra_len = struct.unpack_from("<HH", extra, pos)
        pos += 4
        if pos + extra_len > len(extra):
            raise zipfile.BadZipFile("Corrupt extra field")
        if extra_id == ZIP_UNICODE_PATH_EXTRA_ID:
            data = extra[pos : pos + extra_len]
            if len(data) < 5:
                raise zipfile.BadZipFile("Corrupt unicode path extra field (0x7075)")
            version, field_crc = struct.unpack_from("<BL", data, 0)
            if version == 1 and field_crc == name_crc:
                try:
                    name = data[5:].decode("utf-8")
                except UnicodeDecodeError as e:
                    raise zipfile.BadZipFile(
                        "Corrupt unicode path extra field (0x7075)"
                    ) from e
                if name:
                    return name
        pos += extra_len
    return None


def decode_cd_name(raw_name: bytes, flags: int) -> str:
    encoding = "utf-8" if flags & ZIP_UTF8_FLAG else "cp437"
    try:
        return raw_name.decode(encoding)
    except UnicodeDecodeError as e:
        raise zipfile.BadZipFile(f"Corrupt member name: {e}") from e


def is_dir_name(name: str) -> bool:
    return name.endswith(("/", "\\"))


def decode_name(raw_name: bytes) -> str:
    try:
        return raw_name.decode("utf-8")
    except UnicodeDecodeError:
        return raw_name.decode("cp437")


def safe_rel_path(name: str) -> Optional[Path]:
    if "\x00" in name:
        raise stream_unzip.DataError(f"Null byte in archive member name: {name!r}")
    normalized = name.replace("\\", "/")
    if len(normalized) >= 2 and normalized[1] == ":" and normalized[0].isalpha():
        normalized = normalized[2:]
    parts = [p for p in normalized.split("/") if p not in ("", ".")]
    if ".." in parts:
        raise UnprocessableEntityException(f"{DETAIL_ARCHIVE_MEMBER_REFUSED}: {name}")
    if not parts:
        return None
    return Path(*parts)


def _scan_cd(
    fp: BinaryIO, cd_start: int, cd_size: int, concat: int
) -> Generator[Tuple[str, int, bool, int], None, None]:
    fp.seek(cd_start)
    remaining = cd_size
    while remaining:
        if remaining < ZIP_CD_SIZE:
            raise zipfile.BadZipFile("Truncated central directory")
        header = fp.read(ZIP_CD_SIZE)
        if len(header) != ZIP_CD_SIZE:
            raise zipfile.BadZipFile("Truncated central directory")
        (
            signature,
            _version_made_lo,
            _version_made_hi,
            _version_needed_lo,
            _version_needed_hi,
            flags,
            _compression,
            _mod_time,
            _mod_date,
            _crc32,
            compressed_size,
            uncompressed_size,
            name_len,
            extra_len,
            comment_len,
            _disk_start,
            _internal_attr,
            _external_attr,
            local_header_offset,
        ) = ZIP_CD_STRUCT.unpack(header)
        if signature != ZIP_CD_SIGNATURE:
            raise zipfile.BadZipFile("Bad magic number for central directory")
        entry_size = ZIP_CD_SIZE + name_len + extra_len + comment_len
        if entry_size > remaining:
            raise zipfile.BadZipFile("Truncated central directory")
        raw_name = fp.read(name_len)
        extra = fp.read(extra_len)
        if len(raw_name) != name_len or len(extra) != extra_len:
            raise zipfile.BadZipFile("Truncated central directory")
        fp.seek(comment_len, os.SEEK_CUR)
        if (
            compressed_size == ZIP_SENTINEL_32
            or uncompressed_size == ZIP_SENTINEL_32
            or local_header_offset == ZIP_SENTINEL_32
        ):
            (
                uncompressed_size,
                compressed_size,
                local_header_offset,
            ) = zip64_entry_sizes(
                extra, uncompressed_size, compressed_size, local_header_offset
            )
        abs_offset = concat + local_header_offset
        if abs_offset < 0 or abs_offset > cd_start:
            raise zipfile.BadZipFile("Bad offset for local header")
        name = unicode_path_name(extra, raw_name) or decode_cd_name(raw_name, flags)
        yield name, uncompressed_size, is_dir_name(name), abs_offset
        remaining -= entry_size


def scan_entries_with_offsets(
    fp: BinaryIO,
) -> Tuple[int, Generator[Tuple[str, int, bool, int], None, None]]:
    """
    Return `(cd_start, entries_gen)` where `entries_gen` yields
    `(name, file_size, is_dir, abs_local_header_offset)` for each member
    in the central directory without retaining any member in memory.
    """
    cd_start, cd_size, concat = _central_directory(fp)
    return cd_start, _scan_cd(fp, cd_start, cd_size, concat)


def data_start_offset(fp: BinaryIO) -> int:
    """
    Return the file offset of the first local header referenced in the
    central directory (or `cd_start` if the archive has no entries).
    """
    cd_start, entries = scan_entries_with_offsets(fp)
    min_offset: Optional[int] = None
    for _, _, _, abs_offset in entries:
        if min_offset is None or abs_offset < min_offset:
            min_offset = abs_offset
    return cd_start if min_offset is None else min_offset


def scan_entries(fp: BinaryIO) -> Generator[Tuple[str, int, bool], None, None]:
    """
    Yield `(name, file_size, is_dir)` for each member in the central directory
    without retaining any member in memory.
    """
    _, entries = scan_entries_with_offsets(fp)
    for name, uncompressed_size, is_dir, _ in entries:
        yield name, uncompressed_size, is_dir
