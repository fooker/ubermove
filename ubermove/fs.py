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

import abc
import shutil
import pathlib



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
