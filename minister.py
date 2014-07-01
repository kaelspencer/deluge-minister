#!/usr/bin/python
import click
from pprint import pformat
import os


@click.command()
@click.argument('target', type=click.Path(exists=True, file_okay=False,
                                          resolve_path=True))
@click.option('-d', '--depth', default=0, help='How many directories to '
              'descend into. All files encountered will be added but only '
              'folders at provided depth. Default 0.')
def minister(target, depth):
    print(pformat(iterate_input(target, depth)))


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

if __name__ == '__main__':
    minister()
