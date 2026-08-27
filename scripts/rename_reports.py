#!/usr/bin/env python3
"""
scripts/rename_reports.py

Extracts metadata (submission date YYMMDD, doc type) from PDF report first pages
and generates / executes clean rename plans following the standard format:
`[실험N 또는 프로젝트] [보고서유형] [YYMMDD][추가식별자].pdf`
"""

import os
import re
import sys
import json
import argparse
import unicodedata
from collections import defaultdict
import fitz

def clean_unicode(text: str) -> str:
    """Normalize unicode to NFC form."""
    if not text:
        return ""
    return unicodedata.normalize('NFC', text)

def extract_date_from_text(text: str, filename: str = "") -> str | None:
    """
    Extract YYMMDD format date from first page text or filename fallback.
    """
    text = clean_unicode(text)
    # 1. Explicit 제출일 / 제출일자 / 제출
    m = re.search(r"제출(?:일|일자)?\s*[:\s]*([0-9]{4}[.\-/년\s]+[0-9]{1,2}[.\-/월\s]+[0-9]{1,2})", text)
    if not m:
        m = re.search(r"제출\s*\n\s*:\s*([0-9]{4}[.\-/년\s]+[0-9]{1,2}[.\-/월\s]+[0-9]{1,2})", text)
    if not m:
        # General date YYYY.MM.DD or YYYY년 M월 D일 or YYYY-MM-DD
        m = re.search(r"(20[0-9]{2}[.\-/년\s]+[0-9]{1,2}[.\-/월\s]+[0-9]{1,2})", text)
    
    if m:
        raw = m.group(1)
        dm = re.search(r"(\d{4})[^\d]+(\d{1,2})[^\d]+(\d{1,2})", raw)
        if dm:
            y = dm.group(1)[2:]
            mo = dm.group(2).zfill(2)
            d = dm.group(3).zfill(2)
            return f"{y}{mo}{d}"
            
    # Fallback to filename if text has no date (e.g. 실험10 181130제출 결과보고서.pdf)
    if filename:
        fn_m = re.search(r"(?<!\d)(?:1[0-9]|2[0-9])\d{4}(?!\d)", filename)
        if fn_m:
            return fn_m.group(0)

    return None

def extract_report_metadata(pdf_path: str, category: str, folder_name: str) -> dict:
    """
    Extract report metadata from PDF first page and file information.
    """
    pdf_path = clean_unicode(pdf_path)
    folder_name = clean_unicode(folder_name)
    fname = clean_unicode(os.path.basename(pdf_path))
    
    text = ""
    try:
        doc = fitz.open(pdf_path)
        for p in range(min(2, len(doc))):
            text += "\n" + doc[p].get_text()
        doc.close()
    except Exception as e:
        print(f"Warning: Failed to read {pdf_path}: {e}")
        
    text = clean_unicode(text)
    date_str = extract_date_from_text(text, fname)

    # Sub-part / suffix in filename (e.g. part1, part_1, 예보1, 예보2, (수정), (10.28수정))
    part_suffix = ""
    part_m = re.search(r"(part\d+|part_\d+|예보\d+|\(수정\)|\(\d+\.\d+수정\))", fname, re.IGNORECASE)
    if part_m:
        part_suffix = "_" + part_m.group(1).replace(" ", "")

    subject = folder_name
    doc_type = category
    if "설계계획서" in fname or "설계계획서" in text[:300]:
        doc_type = "설계계획서"
    elif "설계예비보고서" in fname or "설계예비" in text[:300]:
        doc_type = "설계예비보고서"
    elif "설계결과보고서" in fname or "설계결과보고서" in text[:300] or "설계보고서" in text[:300]:
        doc_type = "설계보고서"

    return {
        "old_name": fname,
        "old_path": pdf_path,
        "subject": subject,
        "doc_type": doc_type,
        "date_str": date_str,
        "part_suffix": part_suffix
    }

def build_rename_plan(base_dirs: list[str], category_hint: str = "") -> list[dict]:
    """
    Build rename plan across target directories, resolving conflicts with _1, _2 suffix.
    """
    plan = []
    for bdir in base_dirs:
        bdir = clean_unicode(bdir)
        if not os.path.exists(bdir):
            continue
        cat = category_hint or os.path.basename(bdir)
        for folder in sorted(os.listdir(bdir)):
            norm_folder = clean_unicode(folder)
            fpath = os.path.join(bdir, folder)
            if not os.path.isdir(fpath):
                continue
            norm_fpath = clean_unicode(fpath)
            pdf_files = [f for f in sorted(os.listdir(fpath)) if f.lower().endswith(".pdf")]
            
            parsed_list = []
            name_counts = defaultdict(int)
            for f in pdf_files:
                norm_f = clean_unicode(f)
                full_pdf = os.path.join(fpath, f)
                parsed = extract_report_metadata(full_pdf, cat, norm_folder)
                parsed_list.append(parsed)
                
            for item in parsed_list:
                base_new = f"{item['subject']} {item['doc_type']}"
                if item["date_str"]:
                    base_new += f" {item['date_str']}"
                if item["part_suffix"]:
                    base_new += f"{item['part_suffix']}"
                
                base_new = clean_unicode(base_new)
                name_counts[base_new] += 1
                item["tentative_name"] = base_new
                
            used = defaultdict(int)
            for item in parsed_list:
                t = item["tentative_name"]
                if name_counts[t] > 1:
                    used[t] += 1
                    final_new = f"{t}_{used[t]}.pdf"
                else:
                    final_new = f"{t}.pdf"
                
                final_new = clean_unicode(final_new)
                new_path = clean_unicode(os.path.join(fpath, final_new))
                plan.append({
                    "old_path": clean_unicode(item["old_path"]),
                    "old_name": clean_unicode(item["old_name"]),
                    "new_name": final_new,
                    "new_path": new_path,
                    "folder": norm_folder,
                    "category": clean_unicode(cat)
                })
    return plan

def execute_renaming(plan: list[dict], dry_run: bool = True) -> dict:
    """
    Execute renaming plan using a two-phase transaction-safe renaming approach
    with defensive target collision validation.
    """
    results = {"success": 0, "skipped": 0, "errors": []}
    old_paths_set = {os.path.abspath(op["old_path"]) for op in plan}

    # 1. Validation phase
    target_counts = defaultdict(int)
    for op in plan:
        target_counts[op["new_path"]] += 1
    
    for op in plan:
        old_p = op["old_path"]
        new_p = op["new_path"]
        if old_p == new_p:
            continue

        if target_counts[new_p] > 1:
            err_msg = f"Plan collision: multiple files target the same path '{new_p}'"
            results["errors"].append((old_p, err_msg))
            continue

        # External collision: target exists on disk and is not one of the files being renamed
        if os.path.exists(new_p) and os.path.abspath(new_p) not in old_paths_set:
            err_msg = f"Target collision: unmanaged file '{new_p}' already exists on disk"
            results["errors"].append((old_p, err_msg))

    if results["errors"]:
        return results

    # 2. Execution phase
    if dry_run:
        for op in plan:
            if op["old_path"] == op["new_path"]:
                results["skipped"] += 1
            else:
                results["success"] += 1
        return results

    # Two-phase atomic rename to avoid swap/chain clobbering
    to_rename = [op for op in plan if op["old_path"] != op["new_path"]]
    results["skipped"] = len(plan) - len(to_rename)
    
    temp_mappings = []
    # Phase 1: Rename source files to temporary intermediate paths
    for idx, op in enumerate(to_rename):
        old_p = op["old_path"]
        temp_p = f"{old_p}.__tmp_rename_{idx}__"
        try:
            os.rename(old_p, temp_p)
            temp_mappings.append((temp_p, op["new_path"], old_p))
        except Exception as e:
            results["errors"].append((old_p, f"Phase 1 temp rename failed: {e}"))
            # Rollback Phase 1
            for t_path, _, orig_path in temp_mappings:
                try:
                    os.rename(t_path, orig_path)
                except Exception:
                    pass
            return results

    # Phase 2: Rename intermediate temporary paths to final new paths
    completed = []
    for temp_p, new_p, orig_p in temp_mappings:
        try:
            os.rename(temp_p, new_p)
            completed.append((new_p, orig_p))
            results["success"] += 1
        except Exception as e:
            results["errors"].append((orig_p, f"Phase 2 final rename failed: {e}"))
            # Rollback completed Phase 2 renames and remaining Phase 1 temps
            for fin_p, orig_p in completed:
                try:
                    os.rename(fin_p, orig_p)
                except Exception:
                    pass
            for rem_temp, _, orig_p in temp_mappings[len(completed):]:
                try:
                    os.rename(rem_temp, orig_p)
                except Exception:
                    pass
            return results

    return results

def save_audit_log(plan: list[dict], audit_path: str = "docs/plans/renaming_audit.json", execution_results: dict | None = None) -> str:
    """
    Save rename plan audit JSON log to specified file path.
    """
    audit_path = os.path.abspath(audit_path)
    os.makedirs(os.path.dirname(audit_path), exist_ok=True)

    audit_data = {
        "total_files": len(plan),
        "renames": sum(1 for op in plan if op["old_path"] != op["new_path"]),
        "unchanged": sum(1 for op in plan if op["old_path"] == op["new_path"]),
        "plan": plan,
        "execution": execution_results
    }
    with open(audit_path, "w", encoding="utf-8") as f:
        json.dump(audit_data, f, ensure_ascii=False, indent=2)
    return audit_path

def main(argv=None):
    parser = argparse.ArgumentParser(description="Rename PDF reports based on metadata extraction.")
    parser.add_argument("dirs", nargs="*", help="Base directories containing report folders")
    parser.add_argument("--dry-run", action="store_true", default=False, help="Perform dry run without modifying files (default)")
    parser.add_argument("--apply", action="store_true", default=False, help="Actually rename files")
    parser.add_argument("--audit-log", default="docs/plans/renaming_audit.json", help="Path to save audit log JSON")
    args = parser.parse_args(argv)

    target_dirs = args.dirs
    if not target_dirs:
        # Default target dirs relative to repository root
        script_dir = os.path.dirname(os.path.abspath(__file__))
        repo_root = os.path.dirname(script_dir)
        target_dirs = [
            os.path.join(repo_root, "from_the_past/정리/예비보고서"),
            os.path.join(repo_root, "from_the_past/정리/결과보고서")
        ]

    plan = build_rename_plan(target_dirs)
    print(f"=== Found {len(plan)} PDF files to process ===")
    for op in plan:
        status = "[UNCHANGED]" if op["old_path"] == op["new_path"] else "[RENAME]"
        print(f"{status} [{op['category']}/{op['folder']}] {op['old_name']} -> {op['new_name']}")

    is_dry_run = not args.apply or args.dry_run
    if is_dry_run:
        res = execute_renaming(plan, dry_run=True)
        save_audit_log(plan, audit_path=args.audit_log, execution_results=res)
        print(f"\n[DRY RUN] No files were modified. Success: {res['success']}, Unchanged: {res['skipped']}, Errors: {len(res['errors'])}")
        if res["errors"]:
            for path, err in res["errors"]:
                print(f"  Collision / Error on {path}: {err}")
        print("Run with --apply to execute renames.")
    else:
        res = execute_renaming(plan, dry_run=False)
        save_audit_log(plan, audit_path=args.audit_log, execution_results=res)
        print(f"\n[APPLIED] Success: {res['success']}, Skipped: {res['skipped']}, Errors: {len(res['errors'])}")
        if res["errors"]:
            for path, err in res["errors"]:
                print(f"  Error on {path}: {err}")

    return 0 if not res["errors"] else 1

if __name__ == "__main__":
    sys.exit(main())
