import json
import difflib
import urllib.parse

with open('their.json', 'rb') as d1:
    d1 = json.load(d1)

with open('my.json', 'rb') as d2:
    d2 = json.load(d2)


def compare(path, v1, v2):
    if type(v1) != type(v2):
        return print('+-', path, 'types dont match')

    if path == '/storage/files':
        v1 = {'[{filesystem}:{path}]'.format(**f): f for f in v1}
        v2 = {'[{filesystem}:{path}]'.format(**f): f for f in v2}

    if path == '/systemd/units':
        v1 = {'[{name}]'.format(**u): u for u in v1}
        v2 = {'[{name}]'.format(**u): u for u in v2}

    if isinstance(v1, dict):
        return compare_dict(path, v1, v2)

    if isinstance(v1, list):
        return compare_list(path, v1, v2)

    if isinstance(v1, str) and v1.startswith('data:,'):
        v1 = v1[len('data:,'):]
        v1 = urllib.parse.unquote(v1)

    if isinstance(v2, str) and v2.startswith('data:,'):
        v2 = v2[len('data:,'):]
        v2 = urllib.parse.unquote(v2)

    if v1 != v2:
        if isinstance(v1, str):
            diff = difflib.unified_diff(v1.splitlines(keepends=True), v2.splitlines(keepends=True))
            delta = ''.join(x for x in diff)
            print(path, ':')
            print(delta)
        else:
            print('+-', path, 'different:', v1, v2)


def compare_dict(path, v1, v2):
    for k, v1i in v1.items():
        v2i = v2.get(k)
        compare(path + '/' + k, v1i, v2i)


def compare_list(path, v1, v2):
    for idx, v1i in enumerate(v1):
        try:
            v2i = v2[idx]
        except IndexError:
            v2i = None
        compare(path + '/' + str(idx), v1i, v2i)


compare('', d1, d2)
