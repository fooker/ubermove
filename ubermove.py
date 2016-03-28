import abc
import sys
import shutil
import os.path
import pathlib
import tempfile
import subprocess



class Entry(metaclass=abc.ABCMeta):
    def __init__(self,
                 root: pathlib.Path):
        self.__root = root


    @property
    def root(self):
        return self.__root


    @abc.abstractproperty
    def name(self):
        """ The name of the entity
        """
        pass


    @abc.abstractmethod
    def remove(self):
        """ Remove this entity
        """
        pass


    @abc.abstractmethod
    def rename(self,
               target: pathlib.Path):
        """ Move this entity to the given target
        """
        pass



class FileEntry(Entry):
    def __init__(self,
                 root: pathlib.Path,
                 file: pathlib.PurePath):
        super().__init__(root)

        self.__file = file


    @property
    def file(self):
        return self.__file


    @property
    def path(self):
        return self.root / self.__file


    @property
    def name(self):
        return str(self.__file)


    def remove(self):
        self.path.unlink()


    def rename(self,
               target: pathlib.Path):
        self.path.rename(target)



class ArchiveEntry(Entry):
    def __init__(self,
                 root: pathlib.Path,
                 archive: pathlib.PurePath,
                 member: pathlib.PurePath):
        super().__init__(root)

        self.__archive = archive
        self.__member = member


    @property
    def archive(self):
        return self.__archive


    @property
    def member(self):
        return self.__member


    @property
    def path(self):
        return self.root / self.__archive


    @property
    def name(self):
        return str(self.__archive) + '!/' + str(self.__member)


    def remove(self):
        # Ignore removes on archive members
        pass


    @abc.abstractstaticmethod
    def test(archive: pathlib.Path):
        """ Tests if the given file is an archive
        """
        pass


    @abc.abstractstaticmethod
    def members(archive: pathlib.Path):
        """ Returns an iterator over all member names

            The list of members is reduced to the list of regular files.
        """
        pass



class TarEntry(ArchiveEntry):
    @staticmethod
    def test(archive: pathlib.Path):
        return archive.name.endswith('.tar') \
               or archive.name.endswith('.tar.gz') \
               or archive.name.endswith('.tar.bz2') \
               or archive.name.endswith('.tar.xz')


    @staticmethod
    def members(archive: pathlib.Path):
        import tarfile
        with archive.open('rb') as f, tarfile.TarFile(fileobj=f) as archive:
            return (pathlib.PurePath(member)
                    for member
                    in archive.members
                    if member.isfile())


    def rename(self,
               target: pathlib.Path):
        import tarfile
        with self.path.open('rb') as f, tarfile.TarFile(fileobj=f) as archive:
            with archive.extractfile(str(self.member)) as src, target.open('wb') as dst:
                shutil.copyfileobj(src, dst)



class ZipEntry(ArchiveEntry):
    @staticmethod
    def test(archive: pathlib.Path):
        return archive.name.endswith('.zip')


    @staticmethod
    def members(archive: pathlib.Path):
        import zipfile
        with archive.open('rb') as f, zipfile.ZipFile(f) as archive:
            return (pathlib.PurePath(info.filename)
                    for info
                    in archive.infolist()
                    if not info.filename.endswith('/'))


    def rename(self,
               target: pathlib.Path):
        import zipfile
        with self.path.open('rb') as f, zipfile.ZipFile(f) as archive:
            with archive.open(str(self.member)) as src, target.open('wb') as dst:
                shutil.copyfileobj(src, dst)



class RarEntry(ArchiveEntry):
    @staticmethod
    def test(archive: pathlib.Path):
        return archive.name.endswith('.rar')


    @staticmethod
    def members(archive: pathlib.Path):
        import rarfile
        with archive.open('rb') as f, rarfile.RarFile(f) as archive:
            return (pathlib.PurePath(info.filename)
                    for info
                    in archive.infolist()
                    if not info.isfdir())


    def rename(self,
               target: pathlib.Path):
        import rarfile
        with self.path.open('rb') as f, rarfile.RarFile(f) as archive:
            with archive.open(str(self.member)) as src, target.open('wb') as dst:
                shutil.copyfileobj(src, dst)



def scan(root: pathlib.Path):
    def scan_path(path: pathlib.Path = root):
        if path.is_dir():
            # Got a directory - scan all children recursively
            for child in path.iterdir():
                yield from scan_path(child)

        elif path.is_file():
            # If file is an archive - yield the archive members
            if TarEntry.test(path):
                for member in TarEntry.members(path):
                    yield TarEntry(root, path.relative_to(root), member)

            elif ZipEntry.test(path):
                for member in ZipEntry.members(path):
                    yield ZipEntry(root, path.relative_to(root), member)

            elif RarEntry.test(path):
                for member in RarEntry.members(path):
                    yield RarEntry(root, path.relative_to(root), member)

            else:
                # Yield the file itself
                yield FileEntry(root, path.relative_to(root))


    yield from scan_path()



def parse_args():
    """ Parse the command line arguments
    """

    import argparse

    def path_dir(s: str):
        path = pathlib.Path(s).absolute()

        if not path.is_dir():
            raise argparse.ArgumentTypeError('%r does not exist or is not a directory' % s)

        return path


    # Parse the commandline arguments
    argparser = argparse.ArgumentParser()

    argparser.add_argument('-e', '--editor',
                           metavar='COMMAND',
                           default=os.environ.get('EDITOR', None),
                           type=str,
                           help='the editor command')

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



if __name__ == '__main__':
    main()
