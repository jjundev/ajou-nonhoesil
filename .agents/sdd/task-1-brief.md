### Task 1: Fix `fetchBbBinary` Test Mock Compatibility and Sync Adapter State

**Files:**
- Modify: `/Users/hyunjun_macbook_pro/Documents/Private/ajou/tools/ajou-bb-opencli/adapter/ajou-bb/common.js`
- Test: `/Users/hyunjun_macbook_pro/Documents/Private/ajou/tools/ajou-bb-opencli/tests/common.test.js`
- Test: `/Users/hyunjun_macbook_pro/Documents/Private/ajou/tools/ajou-bb-opencli/tests/download.test.js`

**Interfaces:**
- Consumes: `page.getCookies`, `page.cookies`, `page.evaluate`
- Produces: `fetchBbBinary(page, fileUrl) -> Promise<Buffer>` (only attempts Node session fetch if valid non-empty string cookies are present; falls back to in-page evaluation in test mocks)

- [ ] **Step 1: Write the failing test verification**

Run existing test suite to confirm the 6 failing tests related to unmocked cookies in `fetchBbBinary`:
```bash
npm --prefix /Users/hyunjun_macbook_pro/Documents/Private/ajou/tools/ajou-bb-opencli test
```
Expected: 6 tests failing with `AuthRequiredError: Blackboard Ultra session expired or unauthorized (HTTP 401)`

- [ ] **Step 2: Update `common.js` to guard Node `fetch` with non-empty string `cookieHeader` and sync latest fixes**

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

- [ ] **Step 3: Run test suite to verify all existing tests pass**

```bash
npm --prefix /Users/hyunjun_macbook_pro/Documents/Private/ajou/tools/ajou-bb-opencli test
```
Expected: PASS (114/114 passing, 0 failures)

- [ ] **Step 4: Commit**

```bash
git -C /Users/hyunjun_macbook_pro/Documents/Private/ajou/tools/ajou-bb-opencli add adapter/ajou-bb/common.js
git -C /Users/hyunjun_macbook_pro/Documents/Private/ajou/tools/ajou-bb-opencli commit -m "fix(common): guard session fetch when cookies missing and sync html detection"
```

---

