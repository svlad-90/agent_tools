# Cytoscape.js

`cytoscape.min.js` is Cytoscape.js 3.34.3 (MIT license retained in the bundle).
Source: https://github.com/cytoscape/cytoscape.js/releases/tag/v3.34.3

`cytoscape-webgl-fallback.patch` fixes compatibility issues in the pinned UMD
distribution:

- Canvas layer counts are per-instance, so creating WebGL does not break later
  Canvas instances.
- Failed renderer constructors release observers and WebGL contexts.
- WebGL screen draws emit the same `render` event as Canvas. Application SVG
  connectors otherwise stop following node movement and viewport changes.
- Nodes with outlines use texture rendering, preserving focus and selection
  contours that the simplified WebGL shape shader does not draw.
- Offscreen picking does not clear pending screen redraw flags. Otherwise a
  mouse hit-test can consume a pan, zoom, position or style update without ever
  drawing it to the visible framebuffer.
- Drag-layer updates redraw the complete WebGL scene as well as node-layer
  updates; WebGL uses one visible framebuffer for both layers.
- Pixel-mode mouse wheels use a normalized step of 15 rather than 3 (about
  15% zoom per notch). Initial wheel sampling is capped at the same step.
  Continuous trackpad deltas and line-mode conversion remain unchanged.
  The application omits `wheelSensitivity`; it does not scale every device's
  input or suppress the library's custom-sensitivity warning.

Rebuild with Terser 5.46.1, starting in a temporary directory:

```sh
curl -fLO https://raw.githubusercontent.com/cytoscape/cytoscape.js/v3.34.3/dist/cytoscape.umd.js
patch cytoscape.umd.js /path/to/vendor/cytoscape-webgl-fallback.patch
terser cytoscape.umd.js --compress --mangle --comments '/Copyright/' --output /path/to/vendor/cytoscape.min.js
```

Run `tests/test_graph_renderer.py` after rebuilding, including the real WebGL
context-loss and mixed Canvas/WebGL instance checks.
