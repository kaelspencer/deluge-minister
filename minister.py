#!/usr/bin/python
import click
from pprint import pformat
import os


@click.command()
@click.argument('target', type=click.Path(exists=True, file_okay=False,
                                          resolve_path=True))
def minister(target):
    print(pformat(iterate_input(target, 0)))


def iterate_input(path, depth):
    result = []

    for dir in os.listdir(path):
        if not os.path.islink(dir):
            absolute_path = '%s/%s' % (path, dir)
            result.append((absolute_path, os.path.isdir(absolute_path)))

            if depth > 0 and os.path.isdir(absolute_path):
                result.extend(iterate_input(absolute_path, depth - 1))
    return result

if __name__ == '__main__':
    minister()
