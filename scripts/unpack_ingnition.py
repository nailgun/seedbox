#!/usr/bin/env python

import os
import json
import shutil
import argparse

from seedbox import ignition_parser


def main():
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('file')
    arg_parser.add_argument('dir')
    args = arg_parser.parse_args()

    with open(args.file, 'rb') as f:
        ignition = json.load(f)

    if os.path.exists(args.dir):
        shutil.rmtree(args.dir)

    for path, data in ignition_parser.iter_files(ignition):
        out_path = os.path.join(args.dir, path)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, 'wb') as f:
            f.write(data)


if __name__ == '__main__':
    main()
