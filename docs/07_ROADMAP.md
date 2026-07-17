# 7. Roadmap Beyond the First Deliverable

This roadmap provides architectural direction only. It is not part of the current implementation scope.

## Phase 2 - Change awareness and author review

### Goals

- Identify scenes that may need review after component changes.
- Rebuild only selected or stale scenes locally.
- Make visual review faster.

### Candidate capabilities

- store component revision IDs and source document versions after successful render;
- build a scene-to-component dependency index;
- classify scenes as current, stale, broken, modified, or needs review;
- regenerate stale scenes only;
- create before/after image comparisons and difference heatmaps;
- generate HTML/CSV scene index and build report;
- externalize long instruction Markdown while editing it in the palette;
- add named construction-point callout anchors and projected 2D coordinates;
- add scene tags, chapters, and bulk operations;
- optional user-triggered update of external references with explicit confirmation.

### Architecture impact

- add dependency manifest and render records;
- add revision provider port;
- add image comparison service outside Fusion where possible;
- extend schema through an explicit version migration.

## Phase 3 - Repository and cloud automation

### Goals

- Rebuild manual assets after repository or design changes without a person operating Fusion desktop.
- Publish review artifacts on pull requests.

### Candidate capabilities

- Autodesk Fusion Automation work item for scene rendering;
- GitHub Actions change detection and affected-scene selection;
- upload render reports and images as workflow artifacts;
- open or update documentation pull requests;
- status checks for broken scene references;
- secure Autodesk credential and token handling;
- caching and retry policies.

### Architecture impact

- separate renderer entry point from interactive UI;
- package scene application as a headless-compatible service;
- introduce deterministic environment/version records;
- add cloud job payload schemas;
- enforce idempotent builds.

## Phase 4 - Document publishing

### Goals

- Build complete manuals from scene images and instruction content.

### Candidate paths

- Typst or Quarto CLI publishing for Git-native manuals;
- InDesign desktop script for link refresh and PDF export;
- InDesign Server for fully unattended commercial publishing;
- reusable page templates, warning blocks, parts lists, chapters, and cross-references;
- localization and multiple product variants;
- release PDFs and web manuals.

### Architecture impact

- define a publisher-neutral intermediate manual model;
- separate scene intent from page layout;
- add document templates and publishing adapters;
- preserve scene IDs as cross-system keys.

## Phase 5 - Advanced technical illustration

### Candidate capabilities

- per-occurrence ghosting through custom graphics where supported;
- vector or line-art export path;
- automatic fastener and part callouts from metadata;
- exploded motion paths;
- occlusion checks for required components or anchors;
- view-quality linting based on scene purpose;
- variant/configuration-aware scenes.

## Roadmap sequencing principle

Do not begin Phase 2 until the first deliverable demonstrates that users can comfortably create and maintain scene YAML through the palette. The authoring model and schema are the foundation; automating a poor authoring workflow would only make errors faster.
