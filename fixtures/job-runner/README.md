# Job Runner Fixture

This is a deliberately small calibration target for Highlander. It is not a production job system.

Run the public tests with:

```text
python3 -m unittest discover -s fixtures/job-runner -p 'test_*.py'
```

The fixture contains an intentional lifecycle bug for `T001-race-fix.md`. The public tests cover the ordinary lifecycle; the evaluator adds the duplicate-event case.
