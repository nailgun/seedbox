import json
import difflib
import argparse
import urllib.parse

not_set = object()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('v1')
    parser.add_argument('v2')
    args = parser.parse_args()

    with open(args.v1, 'rb') as v1:
        v1 = json.load(v1)

    with open(args.v2, 'rb') as v2:
        v2 = json.load(v2)

    compare('', v1, v2)


def compare(path, v1, v2):
    if v1 is not_set:
        return print('+', path, '\n\n')

    if v2 is not_set:
        return print('-', path, '\n\n')

    if type(v1) != type(v2):
        return print('+-', path, 'types dont match', '\n\n')

    if path == '/storage/files':
        # TODO: there can be multiple files with same name
        v1 = {'[{filesystem}:{path}]'.format(**f): f for f in v1}
        v2 = {'[{filesystem}:{path}]'.format(**f): f for f in v2}

    if path == '/systemd/units':
        # TODO: there can be multiple units with same name
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
            print(delta, '\n')
        else:
            print(path, ':')
            print('-', v1)
            print('+', v2, '\n\n')


def compare_dict(path, v1, v2):
    keys = set(v1.keys()) | set(v2.keys())
    keys = sorted(keys)

    for k in keys:
        v1i = v1.get(k, not_set)
        v2i = v2.get(k, not_set)
        compare(path + '/' + k, v1i, v2i)


def compare_list(path, v1, v2):
    max_len = max(len(v1), len(v2))

    for idx in range(max_len):
        try:
            v1i = v1[idx]
        except IndexError:
            v1i = not_set
        try:
            v2i = v2[idx]
        except IndexError:
            v2i = not_set
        compare(path + '/' + str(idx), v1i, v2i)


if __name__ == '__main__':
    main()
