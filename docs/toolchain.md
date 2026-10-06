# Toolchain / 工具链

The application has no third-party runtime dependency. Optional notebook/chart versions in `requirements.txt` were verified in an existing Python 3.13 environment; no packages are installed by the application or CI. No external skills or source code are vendored.

应用不依赖第三方运行时包。`requirements.txt` 的可选图表版本在已有 Python 3.13 环境中核对；应用和 CI 不自动安装这些包。

| Component | Source | License | Reviewed reference | Recorded |
| --- | --- | --- | --- | --- |
| GitHub checkout action | https://github.com/actions/checkout | MIT | `11d5960a326750d5838078e36cf38b85af677262` (v4) | 2026-10-06; CI use only |
| GitHub setup-python action | https://github.com/actions/setup-python | MIT | `a26af69be951a213d495a4c3e4e4022e16d87065` (v5) | 2026-10-06; CI use only |
| pandas, optional existing package | https://github.com/pandas-dev/pandas | BSD-3-Clause | 2.3.3 | Verified 2026-10-06; not installed by this change |
| Matplotlib, optional existing package | https://github.com/matplotlib/matplotlib | Matplotlib license (PSF-based) | 3.10.8 | Verified 2026-10-06; not installed by this change |
| NumPy, optional existing package | https://github.com/numpy/numpy | BSD-3-Clause | 2.3.5 | Verified 2026-10-06; not installed by this change |

The ONS importer optionally uses an existing `openpyxl` installation. It checks the source workbook hash before parsing; the reviewed snapshot and licence are documented in [data sources](data-sources.md). CI actions are pinned to full reviewed commit hashes. The routine application workflow reads the CSV snapshot and never downloads data.
