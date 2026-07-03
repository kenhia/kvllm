Write a script `logsum.py` in /workspace. Run as: `python logsum.py <logfile>`.

Each log line looks like: `2026-07-01 12:00:01 ERROR disk full` — a date, a time, a LEVEL token,
then the message (the rest of the line). Blank lines are ignored.

Print, to stdout:
1. One line per level, formatted `LEVEL count`, ordered by count descending, ties broken by
   level name ascending.
2. Then a literal line: `top errors:`
3. Then the up-to-3 most common `ERROR`-level messages, formatted `count× msg` (the character
   between count and message is the multiplication sign `×`, U+00D7, followed by one space),
   ordered by count descending, ties by message ascending.

Example output:
```
INFO 3
ERROR 2
WARN 1
top errors:
2× disk full
1× timeout
```

A seed log file `sample.log` is provided in /workspace so you can try your script.
