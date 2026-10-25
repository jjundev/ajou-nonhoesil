"""In-memory HTTP service for exercising the real sync and download paths."""
import io
import json
from urllib.parse import urlsplit, parse_qs
import urllib.error


class FakeNotion:
    def __init__(self):
        self.pages, self.uploads, self.blocks = {}, {}, {}
        self.serial = 0
        self.append_returns_all = False
        self.fail_after = None
        self.fail_before = None
        self.events = []

    def id(self):
        self.serial += 1
        return f"id-{self.serial}"

    def response(self, obj):
        return io.BytesIO(json.dumps(obj).encode())

    def __call__(self, req, timeout=120):
        url = req.full_url if hasattr(req, "full_url") else req
        if url.startswith("https://files.test/"):
            return io.BytesIO(self.uploads[url.rsplit("/", 1)[1]]["bytes"])
        method, path = req.method, urlsplit(url).path.removeprefix("/v1")
        event = None
        if method == "POST" and path == "/pages":
            event = "page"
        elif method == "PATCH" and path.endswith("/children"):
            event = "insert"
        elif method == "DELETE":
            event = "archive"
        elif method == "POST" and path.endswith("/send"):
            event = "send"
        elif method == "POST" and path == "/file_uploads":
            event = "upload"
        if event and self.fail_before == event:
            self.fail_before = None
            raise urllib.error.URLError("injected before write")
        data = json.loads(req.data) if req.data and not path.endswith("/send") else {}
        if method == "POST" and path == "/pages":
            pid = self.id()
            title = data["properties"]["title"][0]["text"]["content"]
            blocks = []
            for para in data["markdown"].strip().split("\n\n"):
                para = para.strip("\n")
                if not para.strip():
                    continue
                typ = "heading_1" if para.startswith("# ") else "paragraph"
                txt = para.removeprefix("# ") if typ == "heading_1" else para
                b = {"id": self.id(), "type": typ, "parent": {"page_id": pid},
                     "has_children": False, typ: {"rich_text": [{"plain_text": txt}]}}
                blocks.append(b)
                self.blocks[b["id"]] = b
            self.pages[pid] = {"title": title, "blocks": blocks, "parent": data["parent"]["page_id"]}
            result = {"id": pid, "url": f"https://notion.test/{pid}"}
        elif method == "GET" and path.endswith("/children"):
            pid = path.split("/")[2]
            if pid in self.pages:
                blocks = self.pages[pid]["blocks"]
            else:
                blocks = [{"id": id, "type": "child_page", "child_page": {"title": p["title"]}}
                          for id, p in self.pages.items() if p["parent"] == pid]
            result = {"results": blocks, "has_more": False}
        elif method == "POST" and path == "/file_uploads":
            uid = self.id()
            self.uploads[uid] = {"id": uid, "status": "pending"}
            result = dict(self.uploads[uid])
        elif method == "POST" and path.endswith("/send"):
            uid = path.split("/")[2]
            content = req.data.split(b"\r\n\r\n", 1)[1].rsplit(b"\r\n--", 1)[0]
            self.uploads[uid].update(status="uploaded", bytes=content)
            result = {"id": uid, "status": "uploaded"}
        elif method == "GET" and path.startswith("/file_uploads/"):
            result = {k: v for k, v in self.uploads[path.split("/")[2]].items() if k != "bytes"}
        elif method == "PATCH" and path.endswith("/children"):
            pid = path.split("/")[2]
            blocks = self.pages[pid]["blocks"]
            after = data["position"]["after_block"]["id"]
            where = [b["id"] for b in blocks].index(after) + 1
            added = []
            for spec in data["children"]:
                uid = spec["image"]["file_upload"]["id"]
                b = {"id": self.id(), "type": "image", "has_children": False,
                     "parent": {"page_id": pid}, "image": {
                         "type": "file", "file": {"url": f"https://files.test/{uid}"},
                         "caption": spec["image"]["caption"]}}
                self.blocks[b["id"]] = b
                added.append(b)
            blocks[where:where] = added
            result = {"results": blocks if self.append_returns_all else added}
        elif method == "DELETE":
            bid = path.split("/")[2]
            b = self.blocks[bid]
            b["archived"] = True
            self.pages[b["parent"]["page_id"]]["blocks"].remove(b)
            result = b
        elif method == "GET" and path.startswith("/blocks/"):
            result = self.blocks[path.split("/")[2]]
        elif method == "PATCH" and path.startswith("/pages/"):
            pid = path.split("/")[2]
            self.pages[pid]["title"] = data["properties"]["title"]["title"][0]["text"]["content"]
            result = {"id": pid}
        elif method == "GET" and path.endswith("/markdown"):
            pid = path.split("/")[2]
            result = {"markdown": "\n\n".join(
                ("# " if b["type"] == "heading_1" else "") +
                "".join(x.get("plain_text", x.get("text", {}).get("content", ""))
                        for x in b[b["type"]].get("rich_text", []))
                if b["type"] != "image" else "![image](https://files.test/x)"
                for b in self.pages[pid]["blocks"])}
        else:
            raise AssertionError((method, path))
        if event:
            self.events.append(event)
        if event and self.fail_after == event:
            self.fail_after = None
            raise urllib.error.URLError("injected after committed write")
        return self.response(result)
