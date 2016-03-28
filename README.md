ubermove
========

ubermove (short umv) is a mass file management tool utilizing your favorite text editor.

ubermove allows you to move, rename and delete a tree of files by editing a listing using a text editor. This allows you
to use the capabilities provided by your preferred editor, like search and replace, block editing and others for file
management.

The basic concept of ubermove is to have a source and a target directory. On startup the source directory is scanned for
all contained files recursively and the resulting list is opened in a text editor. After editing the file list, the
result is used to rename and delete the files while they are moved to the target directory. While editing the file
listing, two basic operations are supported: renaming and deleting. If the used modifies a line the according file will
be moved to the new location. If the line is empty, the file will be deleted. An unmodified line is moved to the target
using the same name.

In addition to regular files, archives (.tar, .zip, .rar) are supported. The file listing will contain the archive
members attached to the archive filename. While moving an archive, it will be extracted and the members are handled as
any other file.


Installation
------------

ubermove requires python 3.4 and the following python packages:
* rarfile >= 2.7


After installing the requirements, download the code and execute the following command:
```
python setup.py install
```

