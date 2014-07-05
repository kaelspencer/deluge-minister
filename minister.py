#!/usr/bin/python
import click
import json
from pprint import pprint
import os


@click.command()
@click.argument('target', type=click.Path(exists=True, file_okay=False,
                                          resolve_path=True))
@click.option('-d', '--depth', default=0, help='How many directories to '
              'descend into. All files encountered will be added but only '
              'folders at provided depth. Default 0.')
@click.option('-s', '--storage-file', default='minister-storage.json',
              help='The file location to store processed files so duplication '
              'doesn\'t happen in the future.')
def minister(target, depth, storage_file):
    already_processed = load_storage_file(storage_file)
    targets = iterate_input(target, depth, already_processed)
    pprint(targets)
    save_storage_fle(storage_file, [x[0] for x in targets] + already_processed)


def iterate_input(path, depth, already_processed):
    result = []

    for dir in os.listdir(path):
        if not os.path.islink(dir):
            abs_path = '%s/%s' % (path, dir)
            if should_be_included(abs_path, depth == 0, already_processed):
                result.append((abs_path, os.path.isdir(abs_path)))

            if depth > 0 and os.path.isdir(abs_path):
                result.extend(iterate_input(abs_path, depth - 1))
    return result


def should_be_included(path, at_depth, already_processed):
    valid = at_depth or not os.path.isdir(path)
    return valid and path not in already_processed


def save_storage_fle(file, processed):
    f = open(file, 'w')
    f.write(json.dumps(processed, sort_keys=True, indent=4,
                       separators=(',', ': ')))
    f.write('\n')
    f.close()


def load_storage_file(file):
    try:
        f = open(file, 'r')
        lines = f.readlines()
        lines = json.loads(''.join(lines))
        f.close()
        return lines
    except:
        return []

if __name__ == '__main__':
    minister()
