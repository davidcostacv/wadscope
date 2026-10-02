# Geometry preview contract

`render_svg(geometry)` returns deterministic UTF-8-compatible SVG text for validated classic map geometry. It is a floor-plan drawing, not gameplay rendering. Bounds include all vertices; each linedef produces one segment, with its endpoints transformed from world `(x, y)` to SVG `(x, -y)`.

Preserve aspect ratio. Use padding `max(max(width, height) / 25, 1)` and stroke width `max(max(width, height) / 500, 0.25)`. Empty geometry has bounds `(0, 0, 0, 0)` before padding, and degenerate extents still produce a positive viewBox. Numeric formatting must be stable and finite. Default display dimensions may be 1200 by 800 while the viewBox carries world bounds.

Use a dark background, cyan segments for one-sided lines (either side equals `65535`), and amber for two-sided lines. Colors identify raw side-presence metadata, not verified collision or playability. Include an escaped title and description containing the map name and counts, plus an accessible role. Generate XML through the standard library; no script, external asset, executable payload, or raw archive text may be embedded.

`map-svg FILE --map-index N --output PATH [--overwrite]` selects the marker by directory index. It shares extraction's explicit output, source-alias protection, temporary-sibling publication, and overwrite behavior. Defaults retain the archive and geometry limits. Errors use the same exit codes and encoding-safe diagnostics as the archive commands.

Original demonstration geometry must be reproducible from a committed Python builder, with the WAD written only to ignored `local/`. Commit the generated SVG and compare its segments/endpoints with the independently specified geometry. A real Freedoom export may be tested locally; neither an original demonstration map nor a successful geometry export establishes engine playability. An actual engine-reference comparison is a separate release gate.

## Verified checkpoint

The original builder produced 46 vertices, 40 segments, and 12 two-sided segments. The committed SVG reproduces exactly; independent comparison checked every endpoint and color against the original segment specification. A browser rendering check confirmed the drawing and dark background.

The full local suite passes 69 tests on Python 3.12.14. Exporting the hashed Freedoom E1M1 geometry produced 1,175 SVG segments. Its first endpoints are `(2656, -608)` and `(2624, -597)`, matching the independently inspected world coordinates after y inversion. The real export remains ignored, and no engine-reference view is claimed.
