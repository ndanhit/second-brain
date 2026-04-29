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
    
    # Scan for Backlinks
    backlinks = []
    # Only search files ending in .md
    for f in KB_ROOT.rglob("*.md"):
        if f == full_path or "ui" in str(f) or "node_modules" in str(f): continue
        try:
            with open(f, 'r', encoding='utf-8') as src_file:
                content = src_file.read()
                # Search for project-relative link or just filename
                if path in content:
                    src_post = frontmatter.load(f)
                    backlinks.append({
                        "title": src_post.get("title", f.stem),
                        "path": str(f.relative_to(KB_ROOT))
                    })
        except:
            continue

    return {
        "metadata": post.metadata,
        "content": html_content,
        "toc": md.toc if hasattr(md, 'toc') else "",
        "backlinks": backlinks,
        "raw": post.content
    }

@app.get("/api/graph")
async def get_graph():
    """Returns nodes and edges for the graph visualization."""
    nodes = []
    edges = []
    path_to_node = {}
    
    # 1. Collect all nodes
    for i, f in enumerate(KB_ROOT.rglob("*.md")):
        if "ui" in str(f) or "node_modules" in str(f): continue
        try:
            post = frontmatter.load(f)
            rel_path = str(f.relative_to(KB_ROOT))
            node = {
                "id": rel_path,
                "title": post.get("title", f.stem),
                "type": post.get("type", "unknown"),
                "group": rel_path.split('/')[0]
            }
            nodes.append(node)
            path_to_node[rel_path] = node
        except:
            continue

    # 2. Extract edges from links (Standard Markdown & WikiLinks)
    link_pattern = re.compile(r'\[.*?\]\((.*?\.md)\)|\[\[(.*?)\]\]')
    for node in nodes:
        full_path = KB_ROOT / node["id"]
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
                matches = link_pattern.findall(content)
                for m_md, m_wiki in matches:
                    link = m_md if m_md else m_wiki
                    if not link: continue
                    
                    # Clean up link (remove anchors, etc.)
                    link = link.split('#')[0]
                    if not link.endswith('.md'): link += '.md'
                    
                    if link in path_to_node:
                        edges.append({"source": node["id"], "target": link})
        except:
            continue

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
