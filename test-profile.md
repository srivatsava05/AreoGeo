# Automated Test Profile

Profile captured on 9 October 2026 with Python 3.12.14 on Windows, using cProfile and pytest.

## Result

- 25 tests passed in 3.88 seconds of pytest runtime.
- cProfile recorded 3,901,796 calls (3,811,047 primitive) in 4.546 seconds.
- One upstream warning was reported: Starlette currently warns that its `httpx` TestClient adapter is deprecated in favor of `httpx2`.

## Slowest test cases

| Test | Wall time |
| --- | ---: |
| 2,500-feature upload and pagination | 1.33 s |
| Real Shapefile ZIP ingestion and measurement | 0.16 s |
| KML API upload, metadata, and pagination | 0.13 s |
| Unsupported extension and empty upload handling | 0.09 s |

## Cumulative application profile

| Function | Calls | Cumulative time |
| --- | ---: | ---: |
| `upload_file` | 7 | 1.449 s |
| `process_file` | 4 | 1.385 s |
| `measure` | 2,512 | 0.230 s |
| ZIP validation | 7 | 0.116 s |
| Measurement result pagination | 4 | 0.023 s |

The largest single test is the 2,500-feature API case, which took 1.33 seconds. The overall cProfile total includes Python and GIS dependency imports, so it is not a steady-state server benchmark. The KML HTTP test uses a mocked reader; the separate Shapefile test exercises actual GeoPandas/GDAL I/O.
