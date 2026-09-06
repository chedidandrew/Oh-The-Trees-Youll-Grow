#!/usr/bin/env python3
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""Inject a valid OTTYG scheduled-random-tick fixture into chunk 0,0.

This edits an Anvil region file after a clean server shutdown. The next boot must
deserialize the exact nested NBT shape written by OTTYG 11.0.1.
"""

from __future__ import annotations

import argparse
import gzip
import re
import struct
import time
import zlib
from pathlib import Path


SECTOR_BYTES = 4096
HEADER_BYTES = SECTOR_BYTES * 2
MOD_TAG = "ohthetreesyoullgrow"
TICKS_TAG = "scheduled_random_ticks"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def read_u16(data: bytes, offset: int) -> tuple[int, int]:
    require(offset + 2 <= len(data), "Truncated NBT unsigned short")
    return struct.unpack_from(">H", data, offset)[0], offset + 2


def read_i32(data: bytes, offset: int) -> tuple[int, int]:
    require(offset + 4 <= len(data), "Truncated NBT int")
    return struct.unpack_from(">i", data, offset)[0], offset + 4


def read_string(data: bytes, offset: int) -> tuple[str, int]:
    length, offset = read_u16(data, offset)
    end = offset + length
    require(end <= len(data), "Truncated NBT string")
    return data[offset:end].decode("utf-8"), end


def skip_payload(data: bytes, tag_type: int, offset: int) -> int:
    fixed_sizes = {1: 1, 2: 2, 3: 4, 4: 8, 5: 4, 6: 8}
    if tag_type in fixed_sizes:
        end = offset + fixed_sizes[tag_type]
        require(end <= len(data), f"Truncated NBT type {tag_type}")
        return end
    if tag_type == 7:
        length, offset = read_i32(data, offset)
        require(length >= 0, "Negative NBT byte-array length")
        end = offset + length
        require(end <= len(data), "Truncated NBT byte array")
        return end
    if tag_type == 8:
        _, end = read_string(data, offset)
        return end
    if tag_type == 9:
        require(offset < len(data), "Truncated NBT list type")
        element_type = data[offset]
        length, offset = read_i32(data, offset + 1)
        require(length >= 0, "Negative NBT list length")
        for _ in range(length):
            offset = skip_payload(data, element_type, offset)
        return offset
    if tag_type == 10:
        while True:
            require(offset < len(data), "Unterminated NBT compound")
            child_type = data[offset]
            offset += 1
            if child_type == 0:
                return offset
            _, offset = read_string(data, offset)
            offset = skip_payload(data, child_type, offset)
    if tag_type in (11, 12):
        length, offset = read_i32(data, offset)
        require(length >= 0, "Negative NBT array length")
        width = 4 if tag_type == 11 else 8
        end = offset + length * width
        require(end <= len(data), "Truncated NBT array")
        return end
    raise ValueError(f"Unsupported NBT tag type {tag_type}")


def compound_children(data: bytes, offset: int):
    while True:
        require(offset < len(data), "Unterminated NBT compound")
        tag_start = offset
        tag_type = data[offset]
        offset += 1
        if tag_type == 0:
            return
        name, payload_start = read_string(data, offset)
        tag_end = skip_payload(data, tag_type, payload_start)
        yield name, tag_type, tag_start, payload_start, tag_end
        offset = tag_end


def find_child(data: bytes, compound_offset: int, name: str):
    for child in compound_children(data, compound_offset):
        if child[0] == name:
            return child
    return None


def compound_end_marker(data: bytes, compound_offset: int) -> int:
    offset = compound_offset
    for _, _, _, _, tag_end in compound_children(data, compound_offset):
        offset = tag_end
    require(offset < len(data) and data[offset] == 0, "Missing NBT compound end marker")
    return offset


def named_tag(tag_type: int, name: str, payload: bytes) -> bytes:
    encoded = name.encode("utf-8")
    return bytes((tag_type,)) + struct.pack(">H", len(encoded)) + encoded + payload


def fixture_tag(chunk_x: int, chunk_z: int) -> bytes:
    int_array = struct.pack(">i", 3) + struct.pack(">iii", chunk_x * 16, 0, chunk_z * 16)
    tick_list = bytes((11,)) + struct.pack(">i", 1) + int_array
    mod_payload = named_tag(9, TICKS_TAG, tick_list) + b"\x00"
    return named_tag(10, MOD_TAG, mod_payload)


def locate_structures(data: bytes) -> tuple[int, int, int, int, int]:
    require(data and data[0] == 10, "Chunk NBT root is not a compound")
    _, root_payload = read_string(data, 1)
    structures = find_child(data, root_payload, "structures")
    require(structures is not None and structures[1] == 10, "Chunk has no structures compound")
    return structures


def assert_fixture_nbt(data: bytes) -> None:
    structures = locate_structures(data)
    mod = find_child(data, structures[3], MOD_TAG)
    require(mod is not None and mod[1] == 10, "Fixture mod compound missing")
    ticks = find_child(data, mod[3], TICKS_TAG)
    require(ticks is not None and ticks[1] == 9, "Fixture tick list missing")
    payload = ticks[3]
    require(data[payload] == 11, "Fixture list does not contain int arrays")
    length, _ = read_i32(data, payload + 1)
    require(length == 1, "Fixture list is not nonempty")


def inject_nbt(data: bytes, chunk_x: int, chunk_z: int) -> bytes:
    structures = locate_structures(data)
    structures_payload = structures[3]
    existing = find_child(data, structures_payload, MOD_TAG)
    replacement = fixture_tag(chunk_x, chunk_z)
    if existing is None:
        insertion = compound_end_marker(data, structures_payload)
        updated = data[:insertion] + replacement + data[insertion:]
    else:
        updated = data[: existing[2]] + replacement + data[existing[4] :]

    assert_fixture_nbt(updated)
    return updated


def decode_chunk(compression: int, payload: bytes) -> bytes:
    if compression == 1:
        return gzip.decompress(payload)
    if compression == 2:
        return zlib.decompress(payload)
    if compression == 3:
        return payload
    raise ValueError(f"Unsupported Anvil compression type {compression}")


def encode_chunk(compression: int, payload: bytes) -> bytes:
    if compression == 1:
        return gzip.compress(payload, mtime=0)
    if compression == 2:
        return zlib.compress(payload, level=6)
    if compression == 3:
        return payload
    raise ValueError(f"Unsupported Anvil compression type {compression}")


def inject_region(path: Path, chunk_x: int, chunk_z: int) -> None:
    match = re.fullmatch(r"r\.(-?\d+)\.(-?\d+)\.mca", path.name)
    require(match is not None, f"Unexpected region filename: {path.name}")
    region_x, region_z = map(int, match.groups())
    require(region_x == chunk_x >> 5 and region_z == chunk_z >> 5, "Chunk is outside region")

    region = bytearray(path.read_bytes())
    require(len(region) >= HEADER_BYTES, "Truncated Anvil region header")
    index = (chunk_x & 31) + (chunk_z & 31) * 32
    header_offset = index * 4
    location = int.from_bytes(region[header_offset : header_offset + 4], "big")
    sector_offset, sector_count = location >> 8, location & 0xFF
    require(sector_offset >= 2 and sector_count > 0, f"Chunk {chunk_x},{chunk_z} is absent")

    start = sector_offset * SECTOR_BYTES
    require(start + 5 <= len(region), "Chunk location points outside region")
    stored_length = int.from_bytes(region[start : start + 4], "big")
    require(1 < stored_length <= sector_count * SECTOR_BYTES - 4, "Invalid chunk length")
    compression_byte = region[start + 4]
    require(compression_byte & 0x80 == 0, "External Anvil chunk streams are unsupported")
    compression = compression_byte & 0x7F
    compressed = bytes(region[start + 5 : start + 4 + stored_length])
    decoded = decode_chunk(compression, compressed)
    updated = inject_nbt(decoded, chunk_x, chunk_z)
    recompressed = encode_chunk(compression, updated)
    record = struct.pack(">I", len(recompressed) + 1) + bytes((compression_byte,)) + recompressed
    required_sectors = (len(record) + SECTOR_BYTES - 1) // SECTOR_BYTES
    require(required_sectors <= 255, "Updated chunk is too large for an Anvil location entry")

    if required_sectors <= sector_count:
        write_offset = start
        allocated_sectors = sector_count
    else:
        if len(region) % SECTOR_BYTES:
            region.extend(b"\x00" * (SECTOR_BYTES - len(region) % SECTOR_BYTES))
        sector_offset = len(region) // SECTOR_BYTES
        require(sector_offset < 1 << 24, "Region sector offset exceeds Anvil limit")
        write_offset = len(region)
        allocated_sectors = required_sectors
        region[header_offset : header_offset + 4] = (
            (sector_offset << 8) | required_sectors
        ).to_bytes(4, "big")

    padded = record + b"\x00" * (allocated_sectors * SECTOR_BYTES - len(record))
    end = write_offset + len(padded)
    if end > len(region):
        region.extend(b"\x00" * (end - len(region)))
    region[write_offset:end] = padded
    timestamp_offset = SECTOR_BYTES + header_offset
    region[timestamp_offset : timestamp_offset + 4] = int(time.time()).to_bytes(4, "big")
    path.write_bytes(region)

    # Re-open and re-parse the stored chunk so CI cannot pass on an in-memory-only check.
    reread = path.read_bytes()
    location = int.from_bytes(reread[header_offset : header_offset + 4], "big")
    verify_start = (location >> 8) * SECTOR_BYTES
    verify_length = int.from_bytes(reread[verify_start : verify_start + 4], "big")
    verify_compression = reread[verify_start + 4] & 0x7F
    verify_payload = reread[verify_start + 5 : verify_start + 4 + verify_length]
    assert_fixture_nbt(decode_chunk(verify_compression, verify_payload))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("region", type=Path, help="Path to r.0.0.mca")
    parser.add_argument("--chunk-x", type=int, default=0)
    parser.add_argument("--chunk-z", type=int, default=0)
    args = parser.parse_args()
    inject_region(args.region.resolve(), args.chunk_x, args.chunk_z)
    print(
        f"Injected {MOD_TAG}.{TICKS_TAG} fixture into "
        f"chunk {args.chunk_x},{args.chunk_z} in {args.region}"
    )


if __name__ == "__main__":
    main()
