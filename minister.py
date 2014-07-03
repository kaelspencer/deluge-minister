#!/usr/bin/python
import click
import json
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
    targets = iterate_input(target, depth)
    save_output(storage_file, [x[0] for x in targets])


def iterate_input(path, depth):
    result = []

    for dir in os.listdir(path):
        if not os.path.islink(dir):
            absolute_path = '%s/%s' % (path, dir)
            if should_be_included(absolute_path, depth == 0):
                result.append((absolute_path, os.path.isdir(absolute_path)))

            if depth > 0 and os.path.isdir(absolute_path):
                result.extend(iterate_input(absolute_path, depth - 1))
    return result


def should_be_included(path, at_depth):
    return at_depth or not os.path.isdir(path)


def save_output(file, processed):
    f = open(file, 'w')
    f.write(json.dumps(processed, sort_keys=True, indent=4,
                       separators=(',', ': ')))
    f.write('\n')
    f.close()

if __name__ == '__main__':
    minister()
