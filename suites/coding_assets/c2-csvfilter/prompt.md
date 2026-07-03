Write a script `csvfilter.py` in /workspace. Run as:
`python csvfilter.py <file.csv> col=value [col=value ...]`

Read the CSV with a header row. Print (using the `csv` module so quoting is handled correctly)
the header row followed by every data row that matches ALL of the `col=value` conditions
(exact string match on the named column). Preserve the original row order.

- If no conditions are given, print the header and all rows.
- Comparisons are exact string equality on the cell value.

A seed file `data.csv` is provided in /workspace to test against.
