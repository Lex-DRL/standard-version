<div align="center">

# standard-version

[![PyPI][pypi-shield]][pypi-url]
[![GitHub Release][github-release-shield]][github-release-url]

[pypi-shield]: https://img.shields.io/pypi/v/standard-version?logo=pypi
[pypi-url]: https://pypi.org/p/standard-version
[github-release-shield]: https://img.shields.io/github/v/release/Lex-DRL/standard-version?logo=github
[github-release-url]: https://github.com/Lex-DRL/standard-version/releases/latest

*Standardize version string for releases.*
</div>

- Handles `v` prefix.
- Designed to work with pythonic SemVer format, but supports any number of version segments. (`0.1`, `0.0.1`, `0.0.0.1`, ...)
- Turns pre-release specifiers into human-readable names, while preserving other sub-version specifiers:
  - `0.0.1a1` → `0.0.1-alpha1`
  - `1.2.3.4b` → `1.2.3.4-beta`
  - `5.0.rc99` → `5.0-RC99`
  - `1.1 whatever else` → `1.1-whatever-else`
- Ensures dots `.` as separators in numeric part of version, and dashes `-` as suffix separators.
  - Catches any non-alphanumeric characters as version separators, not just dots. So the standardized release name will always be right, regardless of how weird your internal versioning scheme is: be it `1.2:3`, `1-2,3`, `1 2^3` or whatever else - all of these will become `1.2.3`.
- Preserves padded version numbers: `0.001.0002`.
