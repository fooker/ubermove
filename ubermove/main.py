""" This file is part of ubermove.
    Copyright (C) 2016  Dustin Frisch <fooker@lab.sh>

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import sys
import os.path
import pathlib
import tempfile
import subprocess

from ubermove.fs import scan



def parse_args():
    """ Parse the command line arguments
    """

    import argparse
    import textwrap

    def path_dir(s: str):
        path = pathlib.Path(s).absolute()

        if not path.is_dir():
            raise argparse.ArgumentTypeError('%r does not exist or is not a directory' % s)

        return path


    # Parse the commandline arguments
    argparser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=textwrap.dedent('''
            ubermove allows you to move, rename and delete a tree of files by editing a listing using a text editor.
        '''),
        epilog=textwrap.dedent('''
            ubermove  Copyright (C) 2016  Dustin Frisch <fooker@lab.sh>
            This program comes with ABSOLUTELY NO WARRANTY.
            This is free software, and you are welcome to redistribute it
            under certain conditions.
        '''))

    argparser.add_argument('-e', '--editor',
                           metavar='EDITOR',
                           default=os.environ.get('EDITOR', None),
                           type=str,
                           help='the editor command (defaults to $EDITOR)')

    argparser.add_argument('source',
                           metavar='SOURCE',
                           type=path_dir,
                           help='the source path')
    argparser.add_argument('target',
                           metavar='TARGET',
                           type=pathlib.Path,
                           help='the target path')

    return argparser.parse_args()



def main():
    args = parse_args()

    # Check editor
    if args.editor is None:
        print('EDITOR environment variable must be set or -e must be used', file=sys.stderr)
        sys.exit(1)

    # Create temporary file for user editing
    with tempfile.NamedTemporaryFile('w+t') as tmp:

        # Collect the entries and write the entry names to temporary file, each
        # entry in one line
        sources = list(scan(args.source))
        tmp.writelines(source.name + '\n' for source in sources)
        tmp.flush()

        # Open temporary file in editor
        if subprocess.call([args.editor, tmp.name]) is not 0:
            print('Editor did not exit gracefully', file=sys.stderr)
            sys.exit(1)

        # Read back the targets from the temporary file
        tmp.seek(0)
        targets = list(line[:-1] for line in tmp.readlines())

    # Sanity check: the number of targets must match the number of sources
    if len(sources) != len(targets):
        print('Number of lines mismatch', file=sys.stderr)
        sys.exit(1)

    # Execute changes
    for source, target in zip(sources, targets):
        if target == '':
            # If the line is empty, remove the entry
            source.remove()

        else:
            # Ensure the target directory exists
            (args.target / target).parent.mkdir(parents=True, exist_ok=True)

            # As the line was modified, move the entry to the new target
            source.rename(args.target / target)
