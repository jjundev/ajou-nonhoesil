### Task 2: Announcement Attachment Parser in `parser.js`

**Files:**
- Modify: `/Users/hyunjun_macbook_pro/Documents/Private/ajou/tools/ajou-bb-opencli/adapter/ajou-bb/parser.js`
- Test: `/Users/hyunjun_macbook_pro/Documents/Private/ajou/tools/ajou-bb-opencli/tests/parser.test.js`

**Interfaces:**
- Consumes: Raw HTML announcement `body` / `bodyHtml` string and optional `rawAttachments` array
- Produces: `extractAnnouncementAttachments(bodyHtml, rawAttachments = []) -> Array<{ file_name: string, file_size: number|null, file_url: string, mime_type: string|null }>`
- Produces: `normalizeAnnouncement(rawAnnouncement) -> AnnouncementRecord` with populated `attachments: [...]` and accurate `has_attachments: boolean`

- [ ] **Step 1: Write failing unit tests for announcement attachment extraction**

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

- [ ] **Step 2: Run test to verify it fails**

```bash
npm --prefix /Users/hyunjun_macbook_pro/Documents/Private/ajou/tools/ajou-bb-opencli test
```
Expected: FAIL with `extractAnnouncementAttachments is not defined`

- [ ] **Step 3: Implement `extractAnnouncementAttachments` and update `normalizeAnnouncement`**

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

- [ ] **Step 4: Run test to verify it passes**

```bash
npm --prefix /Users/hyunjun_macbook_pro/Documents/Private/ajou/tools/ajou-bb-opencli test
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git -C /Users/hyunjun_macbook_pro/Documents/Private/ajou/tools/ajou-bb-opencli add adapter/ajou-bb/parser.js tests/parser.test.js
git -C /Users/hyunjun_macbook_pro/Documents/Private/ajou/tools/ajou-bb-opencli commit -m "feat(parser): add extractAnnouncementAttachments and populate attachments in normalizeAnnouncement"
```

---

