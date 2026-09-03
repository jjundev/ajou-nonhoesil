# ajou-bb Announcement Attachments Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use subagent-driven-development (recommended) or executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Extend the `ajou-bb` OpenCLI adapter to parse attachments embedded in course announcements and enable downloading them via `opencli ajou-bb download`.

**Architecture:** Extract attachment metadata (`fileName`, `fileSize`, `resourceUrl`) from Blackboard Ultra announcement HTML payloads (`data-bbfile` JSON and `<a>` anchor tags) within `parser.js`, integrate announcement file nodes into the downloadable file collection in `download.js`, and support `--announcements` and unified `--query` / `--all` filtering.

**Tech Stack:** Node.js (ES Modules, `>=24.0.0`), `@jackwener/opencli`, Node.js native test runner (`node:test`, `node:assert/strict`).

## Global Constraints

- Adapter source of truth: `/Users/hyunjun_macbook_pro/Documents/Private/ajou/tools/ajou-bb-opencli/adapter/ajou-bb/`
- Installed runtime location: `~/.opencli/clis/ajou-bb/` (synchronized via `npm run install:local`)
- Zero additional external dependencies (use Node.js built-in APIs)
- All tests in `npm run test` must pass (100% test suite green)
- Strict PII redaction and error boundaries must be preserved
- Safe filename sanitization and overwrite protection must be respected

---

### Task 1: Fix `fetchBbBinary` Test Mock Compatibility and Sync Adapter State

**Files:**
- Modify: `/Users/hyunjun_macbook_pro/Documents/Private/ajou/tools/ajou-bb-opencli/adapter/ajou-bb/common.js`
- Test: `/Users/hyunjun_macbook_pro/Documents/Private/ajou/tools/ajou-bb-opencli/tests/common.test.js`
- Test: `/Users/hyunjun_macbook_pro/Documents/Private/ajou/tools/ajou-bb-opencli/tests/download.test.js`

**Interfaces:**
- Consumes: `page.getCookies`, `page.cookies`, `page.evaluate`
- Produces: `fetchBbBinary(page, fileUrl) -> Promise<Buffer>` (only attempts Node session fetch if valid non-empty string cookies are present; falls back to in-page evaluation in test mocks)

- [x] **Step 1: Write the failing test verification**

Run existing test suite to confirm the 6 failing tests related to unmocked cookies in `fetchBbBinary`:
```bash
npm --prefix /Users/hyunjun_macbook_pro/Documents/Private/ajou/tools/ajou-bb-opencli test
```
Expected: 6 tests failing with `AuthRequiredError: Blackboard Ultra session expired or unauthorized (HTTP 401)`

- [x] **Step 2: Update `common.js` to guard Node `fetch` with non-empty string `cookieHeader` and sync latest fixes**

In `/Users/hyunjun_macbook_pro/Documents/Private/ajou/tools/ajou-bb-opencli/adapter/ajou-bb/common.js`:
Sync the `page.getCookies` and HTML detection fixes from `~/.opencli/clis/ajou-bb/common.js`. Ensure `docCookie` is validated as a non-empty string (`typeof docCookie === 'string' && docCookie.trim()`), and only execute Strategy 2 (Node.js session fetch) if `typeof cookieHeader === 'string' && cookieHeader.trim().length > 0`:
```javascript
            if (typeof page.getCookies === 'function') {
                const cookies = await page.getCookies({ url: 'https://' + AJOU_BB_HOST }).catch(() => []);
                if (Array.isArray(cookies) && cookies.length > 0) {
                    cookieHeader = cookies.map((c) => `${c.name}=${c.value}`).join('; ');
                }
            } else if (typeof page.cookies === 'function') {
                const cookies = await page.cookies('https://' + AJOU_BB_HOST).catch(() => []);
                if (Array.isArray(cookies) && cookies.length > 0) {
                    cookieHeader = cookies.map((c) => `${c.name}=${c.value}`).join('; ');
                }
            }
            if (!cookieHeader && typeof page.evaluate === 'function') {
                const docCookie = await page.evaluate('document.cookie || ""').catch(() => '');
                if (typeof docCookie === 'string' && docCookie.trim()) {
                    cookieHeader = docCookie.trim();
                }
            }

            if (typeof cookieHeader === 'string' && cookieHeader.trim().length > 0) {
                const userAgent = typeof page.evaluate === 'function'
                    ? await page.evaluate('navigator.userAgent').catch(() => '')
                    : 'Mozilla/5.0';

                const headers = {
                    'User-Agent': userAgent || 'Mozilla/5.0',
                    'Referer': AJOU_BB_COURSE_URL,
                    'Accept': '*/*',
                    'Cookie': cookieHeader,
                };

                const nodeResp = await fetch(fullUrl, {
                    headers,
                    redirect: 'follow',
                });

                if (nodeResp.status === 401 || nodeResp.status === 403) {
                    throw new AuthRequiredError(
                        AJOU_BB_HOST,
                        `Blackboard Ultra session expired or unauthorized (HTTP ${nodeResp.status}). Please log in again in Chrome.`,
                    );
                }

                if (nodeResp.ok) {
                    const contentType = nodeResp.headers.get('content-type') || '';
                    const ab = await nodeResp.arrayBuffer();
                    const isHtml = contentType.includes('text/html') || (ab.byteLength > 0 && Buffer.from(ab.slice(0, 50)).toString('utf8').toLowerCase().includes('<html'));
                    if (ab && ab.byteLength > 0 && !isHtml) {
                        return Buffer.from(ab);
                    }
                }
            }
```

- [x] **Step 3: Run test suite to verify all existing tests pass**

```bash
npm --prefix /Users/hyunjun_macbook_pro/Documents/Private/ajou/tools/ajou-bb-opencli test
```
Expected: PASS (114/114 passing, 0 failures)

- [x] **Step 4: Commit**

```bash
git -C /Users/hyunjun_macbook_pro/Documents/Private/ajou/tools/ajou-bb-opencli add adapter/ajou-bb/common.js
git -C /Users/hyunjun_macbook_pro/Documents/Private/ajou/tools/ajou-bb-opencli commit -m "fix(common): guard session fetch when cookies missing and sync html detection"
```

---

### Task 2: Announcement Attachment Parser in `parser.js`

**Files:**
- Modify: `/Users/hyunjun_macbook_pro/Documents/Private/ajou/tools/ajou-bb-opencli/adapter/ajou-bb/parser.js`
- Test: `/Users/hyunjun_macbook_pro/Documents/Private/ajou/tools/ajou-bb-opencli/tests/parser.test.js`

**Interfaces:**
- Consumes: Raw HTML announcement `body` / `bodyHtml` string and optional `rawAttachments` array
- Produces: `extractAnnouncementAttachments(bodyHtml, rawAttachments = []) -> Array<{ file_name: string, file_size: number|null, file_url: string, mime_type: string|null }>`
- Produces: `normalizeAnnouncement(rawAnnouncement) -> AnnouncementRecord` with populated `attachments: [...]` and accurate `has_attachments: boolean`

- [x] **Step 1: Write failing unit tests for announcement attachment extraction**

In `/Users/hyunjun_macbook_pro/Documents/Private/ajou/tools/ajou-bb-opencli/tests/parser.test.js`, add:
```javascript
test('extractAnnouncementAttachments extracts data-bbfile JSON attachments', () => {
    const html = `<p>공지</p><p><a href="https://eclass2.ajou.ac.kr/bbcswebdav/internal/courses/C1/announcements/_1/plan.pdf?token=123" data-bbtype="attachment" data-bbfile="{&quot;fileName&quot;:&quot;plan.pdf&quot;,&quot;fileSize&quot;:97377,&quot;mimeType&quot;:&quot;application/pdf&quot;,&quot;resourceUrl&quot;:&quot;https://eclass2.ajou.ac.kr/bbcswebdav/internal/courses/C1/announcements/_1/plan.pdf?token=123&quot;}">plan.pdf</a></p>`;
    const attachments = extractAnnouncementAttachments(html);
    assert.equal(attachments.length, 1);
    assert.equal(attachments[0].file_name, 'plan.pdf');
    assert.equal(attachments[0].file_size, 97377);
    assert.equal(attachments[0].mime_type, 'application/pdf');
    assert.equal(attachments[0].file_url, 'https://eclass2.ajou.ac.kr/bbcswebdav/internal/courses/C1/announcements/_1/plan.pdf?token=123');
});

test('extractAnnouncementAttachments extracts standard bbcswebdav links as fallback', () => {
    const html = `<p><a href="/bbcswebdav/courses/C1/syllabus.docx">강의계획서.docx</a></p>`;
    const attachments = extractAnnouncementAttachments(html);
    assert.equal(attachments.length, 1);
    assert.equal(attachments[0].file_name, '강의계획서.docx');
    assert.equal(attachments[0].file_url, '/bbcswebdav/courses/C1/syllabus.docx');
});

test('normalizeAnnouncement populates attachments and sets has_attachments correctly', () => {
    const raw = {
        id: '_101_1',
        title: '수업 운영 안내',
        body: `<p><a href="https://eclass2.ajou.ac.kr/bbcswebdav/xid-1" data-bbtype="attachment" data-bbfile="{&quot;fileName&quot;:&quot;guide.pdf&quot;,&quot;fileSize&quot;:1024,&quot;resourceUrl&quot;:&quot;https://eclass2.ajou.ac.kr/bbcswebdav/xid-1&quot;}">guide.pdf</a></p>`,
    };
    const norm = normalizeAnnouncement(raw);
    assert.equal(norm.has_attachments, true);
    assert.equal(norm.attachments.length, 1);
    assert.equal(norm.attachments[0].file_name, 'guide.pdf');
});
```

- [x] **Step 2: Run test to verify it fails**

```bash
npm --prefix /Users/hyunjun_macbook_pro/Documents/Private/ajou/tools/ajou-bb-opencli test
```
Expected: FAIL with `extractAnnouncementAttachments is not defined`

- [x] **Step 3: Implement `extractAnnouncementAttachments` and update `normalizeAnnouncement`**

In `/Users/hyunjun_macbook_pro/Documents/Private/ajou/tools/ajou-bb-opencli/adapter/ajou-bb/parser.js`:
Add `import path from 'node:path';` at top.
```javascript
import path from 'node:path';

/**
 * Extracts attached file metadata from announcement body HTML or raw attachments list.
 */
export function extractAnnouncementAttachments(bodyHtml, rawAttachments = []) {
    const attachments = [];
    const seenUrls = new Set();

    if (Array.isArray(rawAttachments)) {
        for (const att of rawAttachments) {
            if (!att) continue;
            const url = att.url || att.downloadUrl || att.fileUrl || att.resourceUrl;
            if (url && !seenUrls.has(url)) {
                seenUrls.add(url);
                attachments.push({
                    file_name: String(att.fileName || att.name || att.title || 'attachment').trim(),
                    file_size: typeof att.fileSize === 'number' ? att.fileSize : (typeof att.size === 'number' ? att.size : null),
                    file_url: String(url).trim(),
                    mime_type: att.mimeType || att.contentType || null,
                });
            }
        }
    }

    if (typeof bodyHtml === 'string' && bodyHtml.trim()) {
        const bbFileRegex = /<a\b[^>]*\bdata-bbfile="([^"]+)"[^>]*>([\s\S]*?)<\/a>/gi;
        let match;
        while ((match = bbFileRegex.exec(bodyHtml)) !== null) {
            try {
                const decodedJson = match[1]
                    .replace(/&quot;/g, '"')
                    .replace(/&amp;/g, '&')
                    .replace(/&lt;/g, '<')
                    .replace(/&gt;/g, '>');
                const parsed = JSON.parse(decodedJson);
                const fileUrl = parsed.resourceUrl || parsed.url;
                if (fileUrl && !seenUrls.has(fileUrl)) {
                    seenUrls.add(fileUrl);
                    attachments.push({
                        file_name: String(parsed.fileName || parsed.displayName || stripHtml(match[2]) || 'attachment').trim(),
                        file_size: typeof parsed.fileSize === 'number' ? parsed.fileSize : null,
                        file_url: String(fileUrl).trim(),
                        mime_type: parsed.mimeType || null,
                    });
                }
            } catch {
                // Ignore parse errors and continue
            }
        }

        const hrefRegex = /<a\b[^>]*\bhref="([^"]*bbcswebdav[^"]*)"[^>]*>([\s\S]*?)<\/a>/gi;
        while ((match = hrefRegex.exec(bodyHtml)) !== null) {
            const rawHref = match[1].replace(/&amp;/g, '&');
            if (rawHref && !seenUrls.has(rawHref)) {
                seenUrls.add(rawHref);
                const linkText = stripHtml(match[2]).trim();
                let inferredName = linkText;
                if (!inferredName || inferredName === rawHref) {
                    try {
                        const parsedUrl = new URL(rawHref, 'https://eclass2.ajou.ac.kr');
                        inferredName = path.basename(parsedUrl.pathname) || 'attachment';
                    } catch {
                        inferredName = 'attachment';
                    }
                }
                attachments.push({
                    file_name: inferredName,
                    file_size: null,
                    file_url: rawHref,
                    mime_type: null,
                });
            }
        }
    }

    return attachments;
}
```
Update `normalizeAnnouncement`:
```javascript
    const attachments = extractAnnouncementAttachments(bodyHtml, raw.attachments);
    const hasAttachments = Boolean(
        attachments.length > 0
        || raw.hasAttachments
        || (Array.isArray(raw.attachments) && raw.attachments.length > 0),
    );

    return {
        announcement_id: announcementId,
        course_id: courseId,
        title,
        body_text: bodyText,
        body_html: bodyHtml,
        author_name: authorName,
        is_unread: isUnread,
        created_at: createdAt,
        modified_at: modifiedAt,
        has_attachments: hasAttachments,
        attachments,
    };
```

- [x] **Step 4: Run test to verify it passes**

```bash
npm --prefix /Users/hyunjun_macbook_pro/Documents/Private/ajou/tools/ajou-bb-opencli test
```
Expected: PASS

- [x] **Step 5: Commit**

```bash
git -C /Users/hyunjun_macbook_pro/Documents/Private/ajou/tools/ajou-bb-opencli add adapter/ajou-bb/parser.js tests/parser.test.js
git -C /Users/hyunjun_macbook_pro/Documents/Private/ajou/tools/ajou-bb-opencli commit -m "feat(parser): add extractAnnouncementAttachments and populate attachments in normalizeAnnouncement"
```

---

### Task 3: Announcement Attachment Collection and Download in `download.js`

**Files:**
- Modify: `/Users/hyunjun_macbook_pro/Documents/Private/ajou/tools/ajou-bb-opencli/adapter/ajou-bb/download.js`
- Test: `/Users/hyunjun_macbook_pro/Documents/Private/ajou/tools/ajou-bb-opencli/tests/download.test.js`

**Interfaces:**
- Consumes: `fetchBbRest`, `fetchContentHierarchy`, `collectDownloadableFiles`, `extractAnnouncementAttachments`, `resolveCourseId`, `fetchBbBinary`
- Produces: `fetchAnnouncementFiles(page, courseId) -> Promise<Array<DownloadableFile>>`
- Produces: `downloadCommand(page, args)` supporting `--announcements` (boolean flag) and automatically aggregating announcement files when `--all` or `--query` is supplied.

- [x] **Step 1: Write failing unit test for announcement file downloading and registry arg check**

In `/Users/hyunjun_macbook_pro/Documents/Private/ajou/tools/ajou-bb-opencli/tests/download.test.js`, add:
```javascript
test('downloadCommand registers announcements argument in CLI options', () => {
    const reg = getRegistry();
    const downloadEntry = reg.find((entry) => entry.site === 'ajou-bb' && entry.name === 'download');
    assert.ok(downloadEntry, 'download command must be registered');
    const annArg = downloadEntry.args.find((a) => a.name === 'announcements');
    assert.ok(annArg, '--announcements option must be registered');
    assert.equal(annArg.type, 'bool');
});

test('downloadCommand downloads announcement attachments with --announcements flag', async (t) => {
    const tmpDir = await fs.mkdtemp(path.join(os.tmpdir(), 'ajou-bb-ann-dl-'));
    t.after(async () => {
        await fs.rm(tmpDir, { recursive: true, force: true }).catch(() => {});
    });

    const page = createStandardMockPage({
        mockBinaryContent: 'Mock Syllabus Announcement PDF',
    });

    const origEvaluate = page.evaluate;
    page.evaluate = async (script, ...args) => {
        if (typeof script === 'string' && script.includes('/announcements')) {
            return {
                __status: 200,
                __data: {
                    results: [
                        {
                            id: '_ann_1',
                            title: '운영계획 공지',
                            body: `<p><a href="https://eclass2.ajou.ac.kr/bbcswebdav/xid-plan" data-bbtype="attachment" data-bbfile="{&quot;fileName&quot;:&quot;2026_Plan.pdf&quot;,&quot;fileSize&quot;:4096,&quot;resourceUrl&quot;:&quot;https://eclass2.ajou.ac.kr/bbcswebdav/xid-plan&quot;}">2026_Plan.pdf</a></p>`,
                        },
                    ],
                },
            };
        }
        return origEvaluate(script, ...args);
    };

    const results = await downloadCommand(page, {
        course: '회로이론',
        announcements: true,
        out: tmpDir,
    });

    assert.equal(results.length, 1);
    assert.equal(results[0].file_name, '2026_Plan.pdf');
    assert.equal(results[0].status, 'downloaded');
    assert.equal(await fs.stat(path.join(tmpDir, '2026_Plan.pdf')).then(() => true).catch(() => false), true);
});
```

- [x] **Step 2: Run test to verify it fails**

```bash
npm --prefix /Users/hyunjun_macbook_pro/Documents/Private/ajou/tools/ajou-bb-opencli test
```
Expected: FAIL (missing announcement handling in `downloadCommand`)

- [x] **Step 3: Implement `fetchAnnouncementFiles` and integrate into `downloadCommand` in `download.js`**

In `/Users/hyunjun_macbook_pro/Documents/Private/ajou/tools/ajou-bb-opencli/adapter/ajou-bb/download.js`:
Ensure named imports from `./common.js` include `fetchBbRest`:
```javascript
import {
    AJOU_BB_HOST,
    ArgumentError,
    EmptyResultError,
    collectDownloadableFiles,
    fetchBbBinary,
    fetchBbRest,
    fetchContentHierarchy,
    requirePositiveInt,
    resolveCourseId,
    withRedactedErrors,
} from './common.js';
import { extractAnnouncementAttachments, redactDeep } from './parser.js';
```
Add `fetchAnnouncementFiles`:
```javascript
export async function fetchAnnouncementFiles(page, courseId) {
    try {
        const rawData = await fetchBbRest(page, `/learn/api/public/v1/courses/${courseId}/announcements`, {
            params: { limit: 100 },
        });
        const rawList = Array.isArray(rawData) ? rawData : (Array.isArray(rawData?.results) ? rawData.results : []);
        const files = [];

        for (const raw of rawList) {
            const bodyHtml = raw.body ?? raw.body_html ?? '';
            const attachments = extractAnnouncementAttachments(bodyHtml, raw.attachments);
            for (const att of attachments) {
                files.push({
                    content_id: `announcement_${raw.id || raw.announcement_id || 'item'}`,
                    title: raw.title ? `[공지] ${raw.title} - ${att.file_name}` : att.file_name,
                    file_name: att.file_name,
                    file_url: att.file_url,
                    size_bytes: att.file_size,
                    source: 'announcement',
                });
            }
        }
        return files;
    } catch {
        return [];
    }
}
```
Update `downloadCommand`:
```javascript
    const announcementsOnly = Boolean(args.announcements);
    let availableFiles = [];

    if (announcementsOnly) {
        availableFiles = await fetchAnnouncementFiles(page, course.course_id);
    } else {
        const tree = await fetchContentHierarchy(page, course.course_id, null, 1, depth);
        availableFiles = collectDownloadableFiles(tree);
        if (all || query) {
            const annFiles = await fetchAnnouncementFiles(page, course.course_id);
            availableFiles = [...availableFiles, ...annFiles];
        }
    }

    const effectiveAll = all || (announcementsOnly && !query && !contentId);
    const targetFiles = filterFilesForDownload(availableFiles, { query, contentId, all: effectiveAll });
```
In attachment fetching loop inside `downloadCommand`:
```javascript
        if (file.content_id && !String(file.content_id).startsWith('announcement_')) {
            try {
                const attList = await fetchBbRest(page, `/learn/api/public/v1/courses/${course.course_id}/contents/${file.content_id}/attachments`);
                const attachments = Array.isArray(attList?.results) ? attList.results : (Array.isArray(attList) ? attList : []);
                if (attachments.length > 0) {
                    const firstAtt = attachments[0];
                    if (firstAtt.id) {
                        downloadUrl = `/learn/api/public/v1/courses/${course.course_id}/contents/${file.content_id}/attachments/${firstAtt.id}/download`;
                    }
                    if (firstAtt.fileName) {
                        actualFileName = firstAtt.fileName;
                    }
                }
            } catch {
                // Fallback to original file_url
            }
        }
```
Add CLI argument definition:
```javascript
        { name: 'announcements', type: 'bool', default: false, help: 'Download only files attached to course announcements' },
```

- [x] **Step 4: Run test to verify it passes**

```bash
npm --prefix /Users/hyunjun_macbook_pro/Documents/Private/ajou/tools/ajou-bb-opencli test
```
Expected: PASS

- [x] **Step 5: Commit**

```bash
git -C /Users/hyunjun_macbook_pro/Documents/Private/ajou/tools/ajou-bb-opencli add adapter/ajou-bb/download.js tests/download.test.js
git -C /Users/hyunjun_macbook_pro/Documents/Private/ajou/tools/ajou-bb-opencli commit -m "feat(download): add announcement attachments discovery and --announcements support"
```

---

### Task 4: Local Installation and Live Verification

**Files:**
- Modify: `~/.opencli/clis/ajou-bb/*` (via atomic `npm run install:local`)
- Modify: `/Users/hyunjun_macbook_pro/.gemini/config/skills/ajou-bb/SKILL.md` (document `--announcements` option)

**Interfaces:**
- Consumes: Built adapter files in `adapter/ajou-bb/`
- Produces: Production deployment in `~/.opencli/clis/ajou-bb/` and verified CLI command `opencli ajou-bb download <course> --announcements`

- [x] **Step 1: Run `npm run install:local` and `validate`**

```bash
npm --prefix /Users/hyunjun_macbook_pro/Documents/Private/ajou/tools/ajou-bb-opencli run install:local
npm --prefix /Users/hyunjun_macbook_pro/Documents/Private/ajou/tools/ajou-bb-opencli run validate
```
Expected:
- `Installed 12 adapter file(s) to ~/.opencli/clis/ajou-bb`
- `validate` passes with 0 errors.

- [x] **Step 2: Live end-to-end verification**

Run live query download for `논리회로실험` announcement attachment:
```bash
opencli ajou-bb download "_118697_1" --announcements --out ./강의노트/논리회로실험 -f yaml
```
Expected:
- Successfully discovers and downloads `2026-2_논리회로실험 운영계획 (26.09.01).pdf`
- Status: `downloaded` or `skipped (already exists)`
- File is non-dummy and verified.

- [x] **Step 3: Update `SKILL.md` to document announcement downloads**

Update `/Users/hyunjun_macbook_pro/.gemini/config/skills/ajou-bb/SKILL.md`:
Document `--announcements` option in Command Routing Reference table and Workflow 2.

- [x] **Step 4: Commit documentation updates**

```bash
git add docs/plans/2026-09-03-ajou-bb-announcement-attachments.md
```
