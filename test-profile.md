# Automated Test Profile

Profile captured on 9 October 2026 with Python 3.12.14 on Windows, using cProfile and pytest.

## Result

- 26 tests passed in 3.97 seconds of pytest runtime.
- cProfile recorded 3,903,183 calls (3,824,695 primitive) in 4.629 seconds.
- One upstream warning was reported: Starlette currently warns that its `httpx` TestClient adapter is deprecated in favor of `httpx2`.

## Slowest test cases

| Test | Wall time |
| --- | ---: |
| 2,500-feature upload and pagination | 1.33 s |
| Real Shapefile ZIP ingestion and measurement | 0.16 s |
| KML API upload, metadata, and pagination | 0.14 s |
| Unsupported extension and empty upload handling | 0.09 s |
| Real KML/GDAL ingestion and measurement | 0.08 s |

## Cumulative application profile

| Function | Calls | Cumulative time |
| --- | ---: | ---: |
| `upload_file` | 9 | 1.558 s |
| `process_file` | 6 | 1.452 s |
| `measure` | 2,514 | 0.268 s |
| ZIP validation | 9 | 0.104 s |
| Measurement result pagination | 6 | 0.046 s |

The largest single test is the 2,500-feature API case, which took 1.34 seconds. The overall cProfile total includes Python and GIS dependency imports, so it is not a steady-state server benchmark. Both Shapefile and KML integration tests exercise actual GeoPandas/GDAL I/O; a separate KML API test also uses a mocked reader to cover API edge behavior.
