import io
import os
import json
import urllib.parse

from seedbox import utils

encoding = 'utf-8'


def iter_files(ignition):
    if 'storage' in ignition and 'files' in ignition['storage']:
        files = ignition['storage'].pop('files')

        for file in files:
            file_path = file['path']
            if file_path[0] == '/':
                file_path = file_path[1:]
            file_path = os.path.join(file['filesystem'], file_path)

            file_mode = file.get('mode')
            file_uid = file.get('user', {}).get('id')
            file_gid = file.get('group', {}).get('id')

            file_attrs = b''
            if file_mode is not None:
                file_attrs += b'mode: %s\n' % oct(int(file_mode))[2:].encode(encoding)
            if file_uid is not None:
                file_attrs += b'uid: %s\n' % file_uid
            if file_gid is not None:
                file_attrs += b'gid: %s\n' % file_gid

            if file_attrs:
                yield file_path + '.attrs', file_attrs

            file_source = file['contents']['source']
            if file_source.startswith('data:,'):
                file_data = urllib.parse.unquote(file_source[len('data:,'):]).encode(encoding)
            else:
                file_path += '.src'
                file_data = file_source.encode(encoding) + b'\n'

            yield file_path, file_data

    if 'systemd' in ignition and 'units' in ignition['systemd']:
        units = ignition['systemd'].pop('units')
        units_dir_path = os.path.join('root', 'etc', 'systemd', 'system')

        for unit in units:
            unitname = unit['name']
            unit_file_path = os.path.join(units_dir_path, unitname)

            if unit.get('enable'):
                yield unit_file_path + '.enabled', b''

            if 'contents' in unit:
                yield unit_file_path, unit['contents'].encode(encoding)

            if 'dropins' in unit:
                unit_dropins_path = os.path.join(units_dir_path, unitname + '.d')
                for dropin in unit['dropins']:
                    yield os.path.join(unit_dropins_path, dropin['name']), dropin['contents'].encode(encoding)

    yield 'non-fs.json', json.dumps(ignition, indent=2).encode(encoding)


def render_ignition_tgz(ignition):
    tgz_fp = io.BytesIO()
    with utils.TarFile.open(fileobj=tgz_fp, mode='w:gz') as tgz:
        for path, data in iter_files(ignition):
            tgz.adddata(os.path.join('ignition', path), data)
    return tgz_fp.getvalue()
