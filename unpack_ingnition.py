import os
import io
import json
import base64
import shutil
import zipfile
import argparse
import urllib.parse


def main():
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('file')
    arg_parser.add_argument('dir')
    args = arg_parser.parse_args()

    dest_dir = args.dir

    if os.path.exists(dest_dir):
        shutil.rmtree(dest_dir)

    with open(args.file, 'rb') as f:
        ignition = json.load(f)

    if 'storage' in ignition and 'files' in ignition['storage']:
        files = ignition['storage'].pop('files')

        for file in files:
            file_path = file['path']
            if file_path[0] == '/':
                file_path = file_path[1:]

            file_mode = file.get('mode', 0)

            out_path = os.path.join(dest_dir, file['filesystem'], file_path)
            os.makedirs(os.path.dirname(out_path), exist_ok=True)

            data = file['contents']['source']
            data = parse_data(data)

            with open(out_path, 'w') as f:
                f.write(data)

            os.chmod(out_path, file_mode)

            if file_path == 'opt/bootkube/assets.b64':
                zip_data = base64.b64decode(data)
                with open(os.path.join(dest_dir, file['filesystem'], 'opt/bootkube/assets.zip'), 'wb') as f:
                    f.write(zip_data)
                zf = zipfile.ZipFile(io.BytesIO(zip_data))
                zf.extractall(os.path.join(dest_dir, file['filesystem'], 'opt/bootkube'))

    if 'systemd' in ignition and 'units' in ignition['systemd']:
        units = ignition['systemd'].pop('units')
        units_dir_path = os.path.join(dest_dir, 'root', 'system', 'systemd')
        os.makedirs(units_dir_path, exist_ok=True)

        for unit in units:
            unitname = unit['name']
            unit_file_path = os.path.join(units_dir_path, unitname)

            if unit.get('enable'):
                with open(unit_file_path + '.enabled', 'wb'):
                    pass

            if 'contents' in unit:
                with open(unit_file_path, 'w') as f:
                    f.write(unit['contents'])

            if 'dropins' in unit:
                unit_dropins_path = os.path.join(dest_dir, 'root', 'system', 'systemd', unitname + '.d')
                os.makedirs(unit_dropins_path, exist_ok=True)
                for dropin in unit['dropins']:
                    with open(os.path.join(unit_dropins_path, dropin['name']), 'w') as f:
                        f.write(dropin['contents'])

    with open(os.path.join(dest_dir, 'ignition.json'), 'w') as f:
        json.dump(ignition, f, indent=2)


def parse_data(data):
    if data.startswith('data:,'):
        data = data[len('data:,'):]
        data = urllib.parse.unquote(data)
    return data

if __name__ == '__main__':
    main()
