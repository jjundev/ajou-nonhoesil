# Task 2 Report: Announcement Attachment Parser in `parser.js`

## Overview
- **Task**: Task 2 - Announcement Attachment Parser in `parser.js`
- **Working Directory**: `/Users/hyunjun_macbook_pro/Documents/Private/ajou/tools/ajou-bb-opencli`
- **Target Files**:
  - `adapter/ajou-bb/parser.js`
  - `tests/parser.test.js`
- **Commit**: `dc34ffe5147fc183c8d54dc4081b9a52c5d5c4cc` (`feat(parser): add extractAnnouncementAttachments and populate attachments in normalizeAnnouncement`)

## Implementation Details
1. **TDD RED Phase**:
   - Added unit tests in `tests/parser.test.js`:
     - `extractAnnouncementAttachments extracts data-bbfile JSON attachments`: tests parsing of embedded `data-bbfile` attributes with JSON payloads containing `fileName`, `fileSize`, `mimeType`, and `resourceUrl`.
     - `extractAnnouncementAttachments extracts standard bbcswebdav links as fallback`: tests fallback extraction for standard `/bbcswebdav/` anchor links with inferred filenames.
     - `normalizeAnnouncement populates attachments and sets has_attachments correctly`: verifies that `normalizeAnnouncement` populates `attachments` and updates `has_attachments`.
   - Imported `extractAnnouncementAttachments` into `tests/parser.test.js`.
   - Executed `npm test`, verifying failure with `SyntaxError: The requested module '../adapter/ajou-bb/parser.js' does not provide an export named 'extractAnnouncementAttachments'`.

2. **TDD GREEN Phase**:
   - In `adapter/ajou-bb/parser.js`:
     - Imported `path` from `node:path`.
     - Implemented `export function extractAnnouncementAttachments(bodyHtml, rawAttachments = [])`:
       - Supports deduplication via a `seenUrls` Set.
       - Extracts metadata from pre-parsed `rawAttachments` objects if provided.
       - Regex parses `<a data-bbfile="...">` attributes, decodes HTML entities (`&quot;`, `&amp;`, `&lt;`, `&gt;`), parses the JSON payload, extracts `fileName`, `fileSize`, `mimeType`, `resourceUrl`, and falls back to anchor text if filename is missing.
       - Regex parses `<a href="*bbcswebdav*">` links, extracts raw href, deduplicates against `seenUrls`, and infers filename from anchor text or URL path basename.
     - Updated `normalizeAnnouncement`:
       - Invokes `extractAnnouncementAttachments(bodyHtml, raw.attachments)`.
       - Computes `has_attachments` based on extracted attachments count, `raw.hasAttachments`, or `raw.attachments.length`.
       - Adds `attachments` to the returned `AnnouncementRecord`.

3. **Verification**:
   - Executed full test suite (`npm test`). All 117 tests passed (114 previous + 3 new tests).
   - Zero test failures, zero regressions across all course, download, global commands, installer, and parser tests.

4. **Git Commit**:
   - Staged `adapter/ajou-bb/parser.js` and `tests/parser.test.js`.
   - Committed with message: `feat(parser): add extractAnnouncementAttachments and populate attachments in normalizeAnnouncement`.
