# Duplicate-Finder

Simple program made in python for finding duplicate files in folders.

## How it works

The program checks for duplicate files by hashing them with [xxhash](https://xxhash.com) (a very fash hashing algorithm), it starts by only hashing a small portion of the file (for speed) and then rechecks the found files to find true duplicates. The gui is made using [DearPyGUI](https://github.com/hoffstadt/DearPyGui).
