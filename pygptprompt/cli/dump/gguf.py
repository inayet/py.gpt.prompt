#!/usr/bin/env python3
"""
pygptprompt/cli/dump_gguf.py

MIT License

Copyright (c) 2023 Georgi Gerganov

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

NOTE:
    - This is an exact copy of Georgi Gerganov's gguf dump script.
    - This script is included purely as a convenient utility.

Source: https://github.com/ggerganov/llama.cpp/blob/master/gguf-py/scripts/gguf-dump.py
"""
from __future__ import annotations

import argparse
import sys
from typing import Any

import numpy as np

# Necessary to load the local gguf package
from gguf import GGUFReader, GGUFValueType  # noqa: E402


def get_file_host_endian(reader: GGUFReader) -> tuple[str, str]:
    host_endian = "LITTLE" if np.uint32(1) == np.uint32(1).newbyteorder("<") else "BIG"
    if reader.byte_order == "S":
        file_endian = "BIG" if host_endian == "LITTLE" else "LITTLE"
    else:
        file_endian = host_endian
    return (host_endian, file_endian)


# For more information about what field.parts and field.data represent,
# please see the comments in the modify_gguf.py example.
def dump_metadata(reader: GGUFReader, args: argparse.Namespace) -> None:
    host_endian, file_endian = get_file_host_endian(reader)
    print(
        f"* File is {file_endian} endian, script is running on a {host_endian} endian host."
    )
    print(f"\n* Dumping {len(reader.fields)} key/value pair(s)")
    for n, field in enumerate(reader.fields.values(), 1):
        if not field.types:
            pretty_type = "N/A"
        elif field.types[0] == GGUFValueType.ARRAY:
            nest_count = len(field.types) - 1
            pretty_type = (
                "[" * nest_count + str(field.types[-1].name) + "]" * nest_count
            )
        else:
            pretty_type = str(field.types[-1].name)
        print(f"  {n:5}: {pretty_type:10} | {len(field.data):8} | {field.name}", end="")
        if len(field.types) == 1:
            curr_type = field.types[0]
            if curr_type == GGUFValueType.STRING:
                print(
                    " = {0}".format(
                        repr(str(bytes(field.parts[-1]), encoding="utf8")[:60])
                    ),
                    end="",
                )
            elif field.types[0] in reader.gguf_scalar_to_np:
                print(" = {0}".format(field.parts[-1][0]), end="")
        print()
    if args.no_tensors:
        return
    print(f"\n* Dumping {len(reader.tensors)} tensor(s)")
    for n, tensor in enumerate(reader.tensors, 1):
        prettydims = ", ".join(
            "{0:5}".format(d)
            for d in list(tensor.shape) + [1] * (4 - len(tensor.shape))
        )
        print(
            f"  {n:5}: {tensor.n_elements:10} | {prettydims} | {tensor.tensor_type.name:7} | {tensor.name}"
        )


def dump_metadata_json(reader: GGUFReader, args: argparse.Namespace) -> None:
    import json

    host_endian, file_endian = get_file_host_endian(reader)
    metadata: dict[str, Any] = {}
    tensors: dict[str, Any] = {}
    result = {
        "filename": args.model,
        "endian": file_endian,
        "metadata": metadata,
        "tensors": tensors,
    }
    for idx, field in enumerate(reader.fields.values()):
        curr: dict[str, Any] = {
            "index": idx,
            "type": field.types[0].name if field.types else "UNKNOWN",
            "offset": field.offset,
        }
        metadata[field.name] = curr
        if field.types[:1] == [GGUFValueType.ARRAY]:
            curr["array_types"] = [t.name for t in field.types][1:]
            if not args.json_array:
                continue
            itype = field.types[-1]
            if itype == GGUFValueType.STRING:
                curr["value"] = [
                    str(bytes(field.parts[idx]), encoding="utf-8") for idx in field.data
                ]
            else:
                curr["value"] = [
                    pv for idx in field.data for pv in field.parts[idx].tolist()
                ]
        elif field.types[0] == GGUFValueType.STRING:
            curr["value"] = str(bytes(field.parts[-1]), encoding="utf-8")
        else:
            curr["value"] = field.parts[-1].tolist()[0]
    if not args.no_tensors:
        for idx, tensor in enumerate(reader.tensors):
            tensors[tensor.name] = {
                "index": idx,
                "shape": tensor.shape.tolist(),
                "type": tensor.tensor_type.name,
                "offset": tensor.field.offset,
            }
    json.dump(result, sys.stdout)


def main() -> None:
    parser = argparse.ArgumentParser(description="Dump GGUF file metadata")
    parser.add_argument("model", type=str, help="GGUF format model filename")
    parser.add_argument(
        "--no-tensors", action="store_true", help="Don't dump tensor metadata"
    )
    parser.add_argument("--json", action="store_true", help="Produce JSON output")
    parser.add_argument(
        "--json-array",
        action="store_true",
        help="Include full array values in JSON output (long)",
    )
    args = parser.parse_args(None if len(sys.argv) > 1 else ["--help"])
    if not args.json:
        print(f"* Loading: {args.model}")
    reader = GGUFReader(args.model, "r")
    if args.json:
        dump_metadata_json(reader, args)
    else:
        dump_metadata(reader, args)


if __name__ == "__main__":
    main()
