Write a script `dumon.py` in /workspace. Run as: `python dumon.py <threshold-mb>`

Read `du -k` style lines from **stdin**: each line is `<kib>\t<path>` (a size in KiB, a tab,
then a path). For every path whose size is strictly greater than `<threshold-mb>` megabytes
(1 MB = 1024 KiB), print a line: `<mb> MB  <path>` where `<mb>` is the size rounded to the
nearest integer MB and there are **two spaces** between `MB` and the path. Order the output by
size descending (largest first); break ties by path ascending. Blank input lines are ignored.

Example: given stdin
```
2097152	/var/log
512	/etc
1572864	/home
```
`python dumon.py 1` prints:
```
2048 MB  /var/log
1536 MB  /home
```
(`/etc` is 0.5 MB, below the 1 MB threshold.)
