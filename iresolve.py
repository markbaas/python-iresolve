#!/usr/bin/env python

from __future__ import print_function

import json
import os
import os.path
import pkgutil
import re
import sys

from collections import defaultdict
from distutils import dir_util

from pyflakes.api import checkPath

MODULE_BLACKLIST = r'^PyQt5'


class RReporter(object):
    messages = defaultdict(list)

    def __init__(self):
        pass

    def unexpectedError(self, *args, **kwargs):
        pass

    def syntaxError(self, *args, **kwargs):
        pass

    def flake(self, message):
        if message.message.startswith('undefined name'):
            self.messages[message.message_args[0]].append((message.lineno, message.col))


def suppress_output(reverse=False):
    """
    Suppress output
    """
    if reverse:
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__
    else:
        sys.stdout = os.devnull
        sys.stderr = os.devnull


def get_unresolved_variables(f):
    """
    Gets unresolved vars from file
    """
    reporter = RReporter()
    checkPath(f, reporter=reporter)
    return dict(reporter.messages)


def read_objs_from_path(path):
    with open(path) as f:
        exprs = [r'^def (\w+)', r'^class (\w+)', r'^(\w+) =']
        data = f.read()
        objs = [k for r in [re.findall(expr, data, flags=re.MULTILINE)
                            for expr in exprs] if r for k in r]
    return objs


def index_modules(idx=None, path=None):
    """
    Indexes objs from all modules
    """
    suppress_output()
    modules = defaultdict(list)
    pkglist = pkgutil.walk_packages(onerror=lambda x: True)
    print(pkglist)
    if path:
        pkglist = pkgutil.walk_packages(path, onerror=lambda x: True)
    for modl, name, ispkg in pkglist:
        try:
            path = os.path.join(modl.path, name.split('.')[-1])
        except AttributeError:
            # Triggered on zipimport.zipimporter
            continue

        if os.path.isdir(path):
            path = os.path.join(path, '__init__')
        path += '.py'

        objs = []

        if os.path.exists(path):
            try:
                objs = read_objs_from_path(path)
            except:
                continue
        elif not re.search(MODULE_BLACKLIST, name):
            try:
                mod = __import__(name)
                objs = [k for k in dir(mod) if not k.startswith('__')]
            except:
                continue
        else:
            continue

        for obj in objs:
            if name not in modules[obj]:
                modules[obj].append(name)
    suppress_output(True)
    return merge_dicts(idx, dict(modules))


def merge_dicts(d1, d2):
    if not d1:
        return d2
    for v in d2:
        if v in d1:
            for kv in d2[v]:
                if kv not in d1[v]:
                    d1[v].append(kv)
        else:
            d1[v] = d2[v]
    return d1


def get_suggestions(idx, unresolved):
    """
    Returns suggestions
    """
    result = {}
    for u, lines in unresolved.items():
        paths = idx.get(u)
        if paths:
            result[u] = {'paths': paths, 'lineno': lines}
    return result


def output(results, output_format='pretty'):
    if output_format == 'pretty':
        for u, meta in results.items():
            print('* {} can be imported from: {}'.format(u, ', '.join(meta['paths'])))
    elif output_format == 'json':
        print(json.dumps(results))


def get_local_config(parsed):
    dirname = os.path.dirname(parsed.input)
    while os.path.dirname(dirname) != dirname:
        if os.path.exists(os.path.join(dirname, 'iresolve.json')):
            with open(os.path.join(dirname, 'iresolve.json'), 'r') as f:
                config_data = json.loads(f.read())
            if 'path' in config_data:
                original_paths = parsed.path.split(',') if parsed.path else []
                paths = config_data['path'].split(',')
                for path in paths:
                    if path[0] != '/' and path[0] != '\\':
                        original_paths.append(os.path.join(dirname, path))
                    else:
                        original_paths.append(path)
                parsed.path = ','.join(original_paths)
            break
        dirname = os.path.dirname(dirname)
    return parsed


def main():
    import argparse

    default_cache = os.path.join(os.path.expanduser('~'), '.cache/iresolve')
    ap = argparse.ArgumentParser(description='iresolve - Import Resolver')
    ap.add_argument('input', metavar='input', help='input')
    ap.add_argument('--format', choices=['pretty', 'json'], default='pretty', help='Export format')
    ap.add_argument('--cache', default=default_cache, help='Path to cache location')
    ap.add_argument('--index', action='store_true', help='(Re)generate module index')
    ap.add_argument('--path', help='Consider additional paths')
    parsed = ap.parse_args()

    u = get_unresolved_variables(parsed.input)

    # See if there's a local configuration
    parsed = get_local_config(parsed)

    # module cache
    modidx = os.path.realpath(os.path.join(parsed.cache, 'modules.json'))
    if parsed.index or not os.path.exists(modidx):
        idx = index_modules()
        if not os.path.exists(modidx):
            dir_util.mkpath(os.path.dirname(modidx))
        with open(modidx, 'w') as f:
            f.write(json.dumps(idx))
    else:
        with open(modidx) as f:
            idx = json.loads(f.read())

    if parsed.path:
        paths = parsed.path.split(',')
        for path in paths:
            sys.path.append(path)
        idx = index_modules(idx)

    results = get_suggestions(idx, u)
    output(results, parsed.format)
    sys.exit(1)


if __name__ == "__main__":
    main()
