import os
import frontmatter
import subprocess
import re
import webbrowser
import threading
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from typing import List, Dict
import markdown
import json

app = FastAPI(title="Second Brain Dashboard")

# Paths
KB_ROOT = Path(__file__).parent.parent
UI_ROOT = Path(__file__).parent

# Directories excluded from the graph & navigation (operational, not knowledge nodes).
_GRAPH_SKIP_DIRS = ("_archive", "4-archives", "templates", "prompts", "node_modules", ".venv", "ui", "scripts")

# Files excluded — auto-generated indexes, logs, and folder-level READMEs add
# noise to the graph (e.g., knowledge-index.md is a hub linking everywhere).
_GRAPH_SKIP_FILES = ("knowledge-index.md", "CHANGELOG.md", "README.md")

# Match standard markdown link `[text](target.md)` (capture target). Skips images.
_LINK_RE = re.compile(r'(?<!\!)\[[^\]]*\]\(([^)]+\.md[^)]*)\)')


def _is_excluded(rel_path: str) -> bool:
    parts = Path(rel_path).parts
    if any(part in _GRAPH_SKIP_DIRS for part in parts):
        return True
    return parts[-1] in _GRAPH_SKIP_FILES


def _resolve_link(target: str, source_rel: str) -> str:
    """Resolve a markdown link target (relative to source file's dir) to a
    KB-root-relative POSIX path. Returns "" if target is external/anchor-only or
    cannot be resolved cleanly inside the KB."""
    target = target.strip()
    if not target or target.startswith(("http://", "https://", "mailto:", "#", "/")):
        return ""
    target = target.split("#", 1)[0].replace("\\", "/")
    if not target.endswith(".md"):
        return ""
    source_dir = (KB_ROOT / source_rel).parent
    try:
        resolved = (source_dir / target).resolve()
        rel = resolved.relative_to(KB_ROOT.resolve())
    except (ValueError, OSError):
        return ""
    return rel.as_posix()

# Setup static files for images if any
if (KB_ROOT / "attachments").exists():
    app.mount("/attachments", StaticFiles(directory=str(KB_ROOT / "attachments")), name="attachments")

@app.get("/", response_class=HTMLResponse)
async def get_ui():
    index_file = UI_ROOT / "index.html"
    return index_file.read_text()

@app.get("/api/nav")
async def get_navigation():
    """Returns the PARA structure and file tree."""
    categories = {
        "1-projects": [],
        "2-areas": {"systems": [], "architecture": [], "teams": []},
        "3-resources": {"concepts": [], "playbooks": []},
        "4-archives": []
    }
    
    def scan_dir(path: Path):
        files = []
        if path.exists():
            for f in sorted(path.glob("*.md")):
                try:
                    post = frontmatter.load(f)
                    files.append({
                        "name": f.stem,
                        "path": str(f.relative_to(KB_ROOT)),
                        "title": post.get("title", f.stem),
                        "type": post.get("type", "unknown")
                    })
                except:
                    continue
        return files

    # Scan top level
    categories["1-projects"] = scan_dir(KB_ROOT / "1-projects")
    categories["4-archives"] = scan_dir(KB_ROOT / "4-archives")
    
    # Scan nested areas
    categories["2-areas"]["systems"] = scan_dir(KB_ROOT / "2-areas" / "systems")
    categories["2-areas"]["architecture"] = scan_dir(KB_ROOT / "2-areas" / "architecture")
    # Sub-scan ADRs
    adr_path = KB_ROOT / "2-areas" / "architecture" / "adrs"
    if adr_path.exists():
        categories["2-areas"]["architecture"].extend(scan_dir(adr_path))
        
    categories["2-areas"]["teams"] = scan_dir(KB_ROOT / "2-areas" / "teams")
    
    # Scan nested resources
    categories["3-resources"]["concepts"] = scan_dir(KB_ROOT / "3-resources" / "concepts")
    categories["3-resources"]["playbooks"] = scan_dir(KB_ROOT / "3-resources" / "playbooks")
    
    return categories

@app.get("/api/doc/{path:path}")
async def get_document(path: str):
    full_path = KB_ROOT / path
    if not full_path.exists() or not full_path.is_file():
        raise HTTPException(status_code=404, detail="Document not found")
    
    post = frontmatter.load(full_path)
    # Convert markdown to HTML + TOC
    md = markdown.Markdown(extensions=['fenced_code', 'tables', 'toc'])
    html_content = md.convert(post.content)
    
    # Scan for Backlinks — resolve each markdown link in candidate files and
    # match against the requested doc's KB-root-relative path.
    backlinks = []
    target_path = str(Path(path).as_posix())
    for f in KB_ROOT.rglob("*.md"):
        if f == full_path:
            continue
        rel = str(f.relative_to(KB_ROOT))
        if _is_excluded(rel):
            continue
        try:
            content = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for raw_target in _LINK_RE.findall(content):
            if _resolve_link(raw_target, rel) == target_path:
                src_post = frontmatter.load(f)
                backlinks.append({
                    "title": src_post.get("title", f.stem),
                    "path": rel,
                })
                break

    return {
        "metadata": post.metadata,
        "content": html_content,
        "toc": md.toc if hasattr(md, 'toc') else "",
        "backlinks": backlinks,
        "raw": post.content
    }

@app.get("/api/graph")
async def get_graph():
    """Returns nodes and edges for the graph visualization.

    Edges are deduplicated; multiple links between the same pair are folded into
    a single edge with a `value` weight (used for stroke thickness in the UI).
    Each node carries a `degree` (in + out) so the UI can highlight orphans.
    """
    nodes = []
    path_to_node: dict[str, dict] = {}

    # 1. Collect nodes (skip operational dirs).
    for f in KB_ROOT.rglob("*.md"):
        rel_path = str(f.relative_to(KB_ROOT))
        if _is_excluded(rel_path):
            continue
        try:
            post = frontmatter.load(f)
        except Exception:
            continue
        node = {
            "id": rel_path,
            "title": post.get("title", f.stem),
            "type": post.get("type", "unknown"),
            "group": rel_path.split("/")[0],
            "degree": 0,
        }
        nodes.append(node)
        path_to_node[rel_path] = node

    # 2. Extract markdown-link edges. Resolve each link target relative to its
    # source file's directory, then look up the KB-root path in path_to_node.
    edge_counts: dict[tuple[str, str, str], int] = {}
    for node in nodes:
        full = KB_ROOT / node["id"]
        try:
            post = frontmatter.load(full)
        except Exception:
            continue

        # 2a. Body markdown links → "link" edges.
        for raw_target in _LINK_RE.findall(post.content):
            resolved = _resolve_link(raw_target, node["id"])
            if not resolved or resolved == node["id"]:
                continue
            if resolved not in path_to_node:
                continue
            key = (node["id"], resolved, "link")
            edge_counts[key] = edge_counts.get(key, 0) + 1

        # 2b. Frontmatter `sources:` → "source" edges (note → doc derived from it).
        # Sources are repo-root paths like "knowledge-base/notes/foo.md".
        sources = post.get("sources") or []
        if isinstance(sources, str):
            sources = [sources]
        for raw_src in sources:
            if not isinstance(raw_src, str):
                continue
            src = raw_src.strip().lstrip("./")
            if src.startswith("knowledge-base/"):
                src = src[len("knowledge-base/"):]
            src = src.replace("\\", "/")
            if src in path_to_node and src != node["id"]:
                key = (src, node["id"], "source")
                edge_counts[key] = edge_counts.get(key, 0) + 1

    edges = []
    for (src, tgt, kind), count in edge_counts.items():
        edges.append({"source": src, "target": tgt, "value": count, "kind": kind})
        path_to_node[src]["degree"] += 1
        path_to_node[tgt]["degree"] += 1

    return {"nodes": nodes, "links": edges}

@app.get("/api/open/{path:path}")
async def open_in_editor(path: str):
    """Opens a file in the local editor (VS Code or system default)."""
    full_path = KB_ROOT / path
    if not full_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    try:
        # Try VS Code first
        subprocess.run(["code", str(full_path)], check=False)
        # Also try default open on Mac/Linux
        if os.name == 'posix':
            subprocess.run(["open", str(full_path)], check=False)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/search")
async def search(q: str):
    results = []
    # Simple grep-like search in titles and content
    for f in KB_ROOT.rglob("*.md"):
        if "node_modules" in str(f) or "ui" in str(f): continue
        try:
            post = frontmatter.load(f)
            if q.lower() in post.content.lower() or q.lower() in post.get("title", "").lower():
                results.append({
                    "title": post.get("title", f.stem),
                    "path": str(f.relative_to(KB_ROOT)),
                    "type": post.get("type", "unknown")
                })
        except:
            continue
    return results

def open_browser():
    """Opens the browser to the dashboard."""
    webbrowser.open("http://localhost:8888")

if __name__ == "__main__":
    import uvicorn
    # Open browser after a short delay to allow server to start
    threading.Timer(1.5, open_browser).start()
    uvicorn.run(app, host="0.0.0.0", port=8888)
