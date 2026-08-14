"""Download RFC documents published by IETF 6man and v6ops working groups."""

import asyncio
import json
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple

import httpx
from bs4 import BeautifulSoup

BASE_WG_URLS = [
    ("6man", "https://datatracker.ietf.org/wg/6man/documents/"),
    ("v6ops", "https://datatracker.ietf.org/wg/v6ops/documents/"),
]

OUTPUT_DIR = Path("/home/dbshadow/project/RAG-IPv6/data/rfcs")
METADATA_FILE = Path("/home/dbshadow/project/RAG-IPv6/data/metadata.json")


def parse_rfc_list(wg_name: str, html: str) -> List[Dict[str, str]]:
    """Parse HTML page of an IETF WG to extract published RFC documents."""
    soup = BeautifulSoup(html, "html.parser")
    is_rfc_section = False
    rfcs: List[Dict[str, str]] = []

    for tr in soup.find_all("tr"):
        text = tr.get_text()
        if "RFCs (" in text or "RFCs(" in text or text.strip().startswith("RFCs"):
            is_rfc_section = True
            continue
        elif "Internet-Drafts" in text or "Related Internet-Drafts" in text:
            is_rfc_section = False
            continue

        if is_rfc_section:
            # Locate RFC link and title
            for a in tr.find_all("a", href=True):
                href = a["href"]
                if "/doc/rfc" in href:
                    doc_id = href.strip("/").split("/")[-1].lower()
                    # Find full title in the row
                    row_text = tr.get_text(separator=" ", strip=True)
                    # Extract title - clean up document text
                    title_elem = tr.find("td", class_="doc") or tr.find_all("td")[1] if len(tr.find_all("td")) > 1 else a
                    full_title = title_elem.get_text(strip=True) if title_elem else a.get_text(strip=True)
                    
                    # Status column
                    status = ""
                    tds = tr.find_all("td")
                    if len(tds) >= 4:
                        status = tds[3].get_text(strip=True)

                    rfcs.append(
                        {
                            "rfc_id": doc_id,
                            "rfc_number": doc_id.replace("rfc", ""),
                            "title": full_title,
                            "wg": wg_name,
                            "url": f"https://www.rfc-editor.org/rfc/{doc_id}.txt",
                            "datatracker_url": f"https://datatracker.ietf.org/doc/{doc_id}/",
                            "status": status,
                        }
                    )
                    break
    return rfcs


async def fetch_wg_rfcs(client: httpx.AsyncClient, wg_name: str, url: str) -> List[Dict[str, str]]:
    """Fetch WG document page and extract RFC list."""
    response = await client.get(url, follow_redirects=True, timeout=30.0)
    response.raise_for_status()
    return parse_rfc_list(wg_name, response.text)


async def download_rfc(
    client: httpx.AsyncClient,
    rfc: Dict[str, str],
    semaphore: asyncio.Semaphore,
) -> Tuple[str, bool, str]:
    """Download single RFC text file."""
    rfc_id = rfc["rfc_id"]
    file_path = OUTPUT_DIR / f"{rfc_id}.txt"

    if file_path.exists() and file_path.stat().st_size > 0:
        return rfc_id, True, "Already exists"

    async with semaphore:
        try:
            resp = await client.get(rfc["url"], follow_redirects=True, timeout=30.0)
            if resp.status_code == 200:
                file_path.write_text(resp.text, encoding="utf-8", errors="replace")
                return rfc_id, True, "Downloaded"
            else:
                return rfc_id, False, f"HTTP {resp.status_code}"
        except Exception as exc:
            return rfc_id, False, str(exc)


async def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    METADATA_FILE.parent.mkdir(parents=True, exist_ok=True)

    limits = httpx.Limits(max_keepalive_connections=10, max_connections=20)
    async with httpx.AsyncClient(limits=limits, headers={"User-Agent": "RAG-IPv6-Downloader/1.0"}) as client:
        print("Fetching RFC lists from working groups...")
        all_rfcs_dict: Dict[str, Dict[str, str]] = {}

        for wg_name, url in BASE_WG_URLS:
            rfcs = await fetch_wg_rfcs(client, wg_name, url)
            print(f"[{wg_name}] Found {len(rfcs)} RFCs")
            for item in rfcs:
                doc_id = item["rfc_id"]
                if doc_id in all_rfcs_dict:
                    # Update WG if shared between groups
                    existing_wg = all_rfcs_dict[doc_id]["wg"]
                    if wg_name not in existing_wg:
                        all_rfcs_dict[doc_id]["wg"] = f"{existing_wg}, {wg_name}"
                else:
                    all_rfcs_dict[doc_id] = item

        unique_rfcs = list(all_rfcs_dict.values())
        print(f"Total unique RFCs to download: {len(unique_rfcs)}")

        # Save metadata
        METADATA_FILE.write_text(json.dumps(unique_rfcs, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Saved metadata to {METADATA_FILE}")

        # Download RFCs concurrently
        semaphore = asyncio.Semaphore(10)
        tasks = [download_rfc(client, rfc, semaphore) for rfc in unique_rfcs]
        
        success_count = 0
        failed_count = 0

        for future in asyncio.as_completed(tasks):
            rfc_id, success, message = await future
            if success:
                success_count += 1
            else:
                failed_count += 1
                print(f"[FAILED] {rfc_id}: {message}")

        print(f"\nDownload completed: {success_count} succeeded, {failed_count} failed.")
        print(f"Files saved in: {OUTPUT_DIR}")


if __name__ == "__main__":
    asyncio.run(main())
