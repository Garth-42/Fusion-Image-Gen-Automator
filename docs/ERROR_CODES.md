# Error Code Catalog

## Blocking errors

| Code | Meaning |
|---|---|
| `NO_ACTIVE_FUSION_DESIGN` | Active document is not a supported Fusion design |
| `PROJECT_NOT_ASSOCIATED` | Active document has no project association |
| `PROJECT_ROOT_UNRESOLVED` | Local path mapping is missing or invalid |
| `PROJECT_ID_MISMATCH` | Document, local mapping, and manifest disagree |
| `SCHEMA_VERSION_MISSING` | YAML lacks schema version |
| `SCHEMA_VERSION_UNSUPPORTED` | YAML version is newer or otherwise unsupported |
| `YAML_PARSE_FAILED` | YAML cannot be safely parsed |
| `SCENE_REFERENCE_MISSING` | Referenced Fusion entity is absent |
| `DUPLICATE_OCCURRENCE_ID` | More than one occurrence uses the same UUID |
| `DUPLICATE_COMPONENT_ID` | More than one component uses the same UUID |
| `CAMERA_INVALID` | Camera values are non-finite or geometrically invalid |
| `TRANSFORM_INVALID` | Transform is malformed or non-finite |
| `OUTPUT_PATH_UNSAFE` | Resolved output path escapes project root |
| `OPACITY_REPLAY_UNSUPPORTED` | Requested opacity state cannot be replayed safely |
| `STATE_RESTORE_FAILED` | Pre-operation Fusion state could not be fully restored |
| `RENDER_FAILED` | Fusion image export failed |
| `OPERATION_IN_PROGRESS` | Another state-mutating operation owns the lock |

## Warnings

| Code | Meaning |
|---|---|
| `DOCUMENT_ID_WEAK` | Source document lacks a stable data-file identifier |
| `DOCUMENT_NOT_UP_TO_DATE` | Fusion reports out-of-date external references |
| `UNLISTED_OCCURRENCE_HIDDEN` | New occurrence was absent from scene and hidden |
| `OPACITY_REPLAY_APPROXIMATE` | Effective opacity may differ because of inheritance |
| `THUMBNAIL_FAILED` | Final render succeeded but thumbnail failed |
| `OUTPUT_IMAGE_MISSING` | Scene is valid but has no final image |
| `THUMBNAIL_MISSING` | Scene is valid but has no thumbnail |
| `SOURCE_DOCUMENT_MISMATCH` | Scene source metadata differs from active document |
