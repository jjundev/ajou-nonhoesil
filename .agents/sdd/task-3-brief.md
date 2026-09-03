### Task 3: Announcement Attachment Collection and Download in `download.js`

**Files:**
- Modify: `/Users/hyunjun_macbook_pro/Documents/Private/ajou/tools/ajou-bb-opencli/adapter/ajou-bb/download.js`
- Test: `/Users/hyunjun_macbook_pro/Documents/Private/ajou/tools/ajou-bb-opencli/tests/download.test.js`

**Interfaces:**
- Consumes: `fetchBbRest`, `fetchContentHierarchy`, `collectDownloadableFiles`, `extractAnnouncementAttachments`, `resolveCourseId`, `fetchBbBinary`
- Produces: `fetchAnnouncementFiles(page, courseId) -> Promise<Array<DownloadableFile>>`
- Produces: `downloadCommand(page, args)` supporting `--announcements` (boolean flag) and automatically aggregating announcement files when `--all` or `--query` is supplied.

- [ ] **Step 1: Write failing unit test for announcement file downloading and registry arg check**

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

- [ ] **Step 2: Run test to verify it fails**

```bash
npm --prefix /Users/hyunjun_macbook_pro/Documents/Private/ajou/tools/ajou-bb-opencli test
```
Expected: FAIL (missing announcement handling in `downloadCommand`)

- [ ] **Step 3: Implement `fetchAnnouncementFiles` and integrate into `downloadCommand` in `download.js`**

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

- [ ] **Step 4: Run test to verify it passes**

```bash
npm --prefix /Users/hyunjun_macbook_pro/Documents/Private/ajou/tools/ajou-bb-opencli test
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git -C /Users/hyunjun_macbook_pro/Documents/Private/ajou/tools/ajou-bb-opencli add adapter/ajou-bb/download.js tests/download.test.js
git -C /Users/hyunjun_macbook_pro/Documents/Private/ajou/tools/ajou-bb-opencli commit -m "feat(download): add announcement attachments discovery and --announcements support"
```

---

