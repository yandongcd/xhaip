"""
Medical Standards Downloader
----------------------------
Downloads clinical guidelines, consensus statements, and medical standards
from freely accessible sources (PubMed Central, NICE, WHO, CDC, etc.)

Sources:
  - PubMed / PubMed Central (Entrez API) - guidelines published in journals
  - NICE (UK) - all guidelines freely available as PDF
  - WHO IRIS - WHO institutional repository
  - CDC - freely available guidelines
  - AHRQ - US Agency for Healthcare Research guidelines
  - National Guideline Clearinghouse (archive)

Usage:
  python download_standards.py --list             # Show available standards
  python download_standards.py --all              # Download all available
  python download_standards.py --source nice      # Download from specific source
  python download_standards.py --id A1            # Download for specific doc
"""

import json
import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import requests

# Optional: biopython for PubMed
try:
    from Bio import Entrez
    BIOPYTHON_AVAILABLE = True
except ImportError:
    BIOPYTHON_AVAILABLE = False

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

# ─── Configuration ──────────────────────────────────────────────────────────

OUTPUT_DIR = Path(__file__).parent.parent.parent / "docs" / "standards"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

ENTREZ_EMAIL = os.environ.get("ENTREZ_EMAIL", "researcher@hospital.cn")
ENTREZ_API_KEY = os.environ.get("ENTREZ_API_KEY", "")

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "MedicalStandardsDownloader/1.0 (academic-research; xhaip-project)",
})

# ─── Data Models ────────────────────────────────────────────────────────────

@dataclass
class Standard:
    """A medical standard/guideline to download."""
    id: str
    title: str
    title_cn: str = ""
    source: str = ""          # pubmed, nice, who, cdc, ahrq
    source_id: str = ""        # PMID, NICE guideline number, WHO ISBN
    url: str = ""
    file_type: str = "pdf"
    category: str = ""         # guideline, consensus, standard, regulation
    specialty: str = ""        # cardiology, oncology, etc.
    priority: str = ""         # P0, P1, P2
    downloaded: bool = False
    local_path: str = ""


# ─── Source Registry ─────────────────────────────────────────────────────────

# P0 key standards missing from xHAIP - prioritized for download
PRIORITY_STANDARDS = [
    # ── AI Regulatory ──
    Standard(id="NMPA-AI-REG", title="AI Medical Device Registration Review Guideline",
             title_cn="人工智能医疗器械注册审查指导原则", source="nmpa", priority="P0",
             url="https://www.nmpa.gov.cn/ylqx/ylqxggtg/20220309111021184.html"),
    Standard(id="ISO-14971", title="ISO 14971:2019 Medical devices - Application of risk management",
             source="iso", priority="P0", category="standard"),
    Standard(id="IEC-62304", title="IEC 62304:2006 Medical device software - Software life cycle processes",
             source="iec", priority="P0", category="standard"),

    # ── Clinical Core Guidelines (PubMed-accessible) ──
    Standard(id="ESC-CMP-2023", title="2023 ESC Guidelines for the management of cardiomyopathies",
             source="pubmed", priority="P0", category="guideline", specialty="cardiology",
             url="https://pubmed.ncbi.nlm.nih.gov/37622666/"),
    Standard(id="ESC-AFIB-2024", title="2024 ESC Guidelines for the management of atrial fibrillation",
             source="pubmed", priority="P0", category="guideline", specialty="cardiology"),
    Standard(id="AHA-ASA-STROKE-2019", title="2019 AHA/ASA Guidelines for the Early Management of Acute Ischemic Stroke",
             source="pubmed", priority="P0", category="guideline", specialty="neurology",
             url="https://pubmed.ncbi.nlm.nih.gov/31662037/"),
    Standard(id="KDIGO-AKI-2024", title="KDIGO 2024 Clinical Practice Guideline for Acute Kidney Injury",
             source="pubmed", priority="P0", category="guideline", specialty="nephrology"),
    Standard(id="GOLD-COPD-2024", title="Global Strategy for the Diagnosis, Management, and Prevention of COPD (GOLD 2024)",
             source="pubmed", priority="P0", category="guideline", specialty="respiratory"),
    Standard(id="ADA-DM-2025", title="Standards of Care in Diabetes - 2025",
             source="pubmed", priority="P0", category="guideline", specialty="endocrinology",
             url="https://pubmed.ncbi.nlm.nih.gov/?term=ADA+standards+of+care+diabetes+2025"),
    Standard(id="AHA-ACC-VALVE-2020", title="2020 ACC/AHA Guideline for the Management of Valvular Heart Disease",
             source="pubmed", priority="P0", category="guideline", specialty="cardiology",
             url="https://pubmed.ncbi.nlm.nih.gov/33332150/"),

    # ── NICE Guidelines (freely available) ──
    Standard(id="NICE-CG124", title="Hip fracture: management (CG124)",
             source="nice", priority="P0", category="guideline", specialty="orthopedics",
             url="https://www.nice.org.uk/guidance/cg124"),
    Standard(id="NICE-CG167", title="Abdominal aortic aneurysm: diagnosis and management (CG167)",
             source="nice", priority="P1", category="guideline", specialty="vascular",
             url="https://www.nice.org.uk/guidance/cg167"),
    Standard(id="NICE-CG148", title="Urinary incontinence in women: management (CG148)",
             source="nice", priority="P1", category="guideline", specialty="urology",
             url="https://www.nice.org.uk/guidance/cg148"),

    # ── WHO Guidelines ──
    Standard(id="WHO-AI-ETHICS", title="Ethics and governance of artificial intelligence for health",
             source="who", priority="P0", category="guideline",
             url="https://www.who.int/publications/i/item/9789240029200"),
    Standard(id="WHO-PATIENT-SAFETY", title="Global Patient Safety Action Plan 2021-2030",
             source="who", priority="P1", category="framework",
             url="https://www.who.int/publications/i/item/9789240032705"),
    Standard(id="WHO-HEARTS", title="HEARTS: Technical package for cardiovascular disease management",
             source="who", priority="P1", category="framework", specialty="cardiology",
             url="https://www.who.int/publications/i/item/9789240001367"),

    # ── CDC Guidelines ──
    Standard(id="CDC-AMS", title="Core Elements of Hospital Antibiotic Stewardship Programs",
             source="cdc", priority="P1", category="guideline", specialty="infectious-disease",
             url="https://www.cdc.gov/antibiotic-use/core-elements/hospital.html"),

    # ── ASCO Guidelines ──
    Standard(id="ASCO-CHEMO-SAFETY", title="ASCO/ONS Chemotherapy Administration Safety Standards",
             source="pubmed", priority="P0", category="standard", specialty="oncology",
             url="https://pubmed.ncbi.nlm.nih.gov/27870573/"),

    # ── Data Standards ──
    Standard(id="FHIR-R4", title="HL7 FHIR R4 Specification",
             source="hl7", priority="P0", category="standard",
             url="https://hl7.org/fhir/R4/"),
    Standard(id="SNOMED-CT", title="SNOMED CT - Systematized Nomenclature of Medicine",
             source="snomed", priority="P0", category="standard",
             url="https://www.snomed.org/"),
    Standard(id="LOINC", title="LOINC - Logical Observation Identifiers Names and Codes",
             source="loinc", priority="P0", category="standard",
             url="https://loinc.org/"),
]


# ─── PubMed/PMC Downloader ──────────────────────────────────────────────────

class PubMedDownloader:
    """Fetch guidelines and consensus papers from PubMed/PMC."""

    def __init__(self):
        if not BIOPYTHON_AVAILABLE:
            raise ImportError("biopython required: pip install biopython")
        Entrez.email = ENTREZ_EMAIL
        if ENTREZ_API_KEY:
            Entrez.api_key = ENTREZ_API_KEY

    def search(self, query: str, max_results: int = 10) -> list[str]:
        """Search PubMed for guidelines matching query."""
        # Add guideline filter to query
        full_query = f"({query}) AND (guideline[ptyp] OR consensus[tiab] OR standard[tiab])"
        log.info("Searching PubMed: %s", query)
        try:
            handle = Entrez.esearch(db="pubmed", term=full_query, retmax=max_results, sort="relevance")
            records = Entrez.read(handle)
            handle.close()
            return records.get("IdList", [])
        except Exception as e:
            log.error("PubMed search failed: %s", e)
            return []

    def get_details(self, pmids: list[str]) -> list[dict]:
        """Fetch article details for given PMIDs."""
        if not pmids:
            return []
        log.info("Fetching details for %d articles", len(pmids))
        try:
            handle = Entrez.efetch(db="pubmed", id=",".join(pmids), rettype="xml", retmode="xml")
            records = Entrez.read(handle)
            handle.close()
            articles = []
            for article in records.get("PubmedArticle", []):
                medline = article["MedlineCitation"]
                info = {
                    "pmid": str(medline["PMID"]),
                    "title": str(medline["Article"].get("ArticleTitle", "")),
                    "journal": str(medline["Article"]["Journal"].get("Title", "")),
                    "year": str(medline["Article"]["Journal"]["JournalIssue"]["PubDate"].get("Year", "")),
                    "doi": "",
                    "has_pmc": False,
                    "pmcid": "",
                }
                # Extract DOI
                for eid in medline["Article"].get("ELocationID", []):
                    if eid.attributes.get("EIdType") == "doi":
                        info["doi"] = str(eid)
                # Check PMC availability
                for other_id in medline.get("OtherID", []):
                    if str(other_id).startswith("PMC"):
                        info["pmcid"] = str(other_id)
                        info["has_pmc"] = True
                articles.append(info)
            return articles
        except Exception as e:
            log.error("Failed to fetch article details: %s", e)
            return []

    def download_pmc(self, pmcid: str, output_dir: Path) -> Path | None:
        """Download full text PDF from PubMed Central (open access only)."""
        output_dir.mkdir(parents=True, exist_ok=True)
        pdf_url = f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/pdf/"
        try:
            resp = SESSION.get(pdf_url, timeout=30)
            if resp.status_code == 200 and "application/pdf" in resp.headers.get("content-type", ""):
                filepath = output_dir / f"{pmcid}.pdf"
                filepath.write_bytes(resp.content)
                log.info("Downloaded PMC: %s -> %s (%d bytes)", pmcid, filepath.name, len(resp.content))
                return filepath
            else:
                log.warning("PMC %s: not downloadable (status=%d)", pmcid, resp.status_code)
                return None
        except Exception as e:
            log.error("PMC download failed %s: %s", pmcid, e)
            return None


# ─── NICE Downloader ────────────────────────────────────────────────────────

class NICEDownloader:
    """Download NICE guidelines (all freely available as PDF)."""

    NICE_API = "https://www.nice.org.uk"

    def get_guideline_pdf(self, nice_id: str, output_dir: Path) -> Path | None:
        """Download NICE guideline PDF by its ID (e.g., CG124, NG106)."""
        output_dir.mkdir(parents=True, exist_ok=True)
        # NICE PDF URL pattern
        pdf_url = f"{self.NICE_API}/guidance/{nice_id.lower()}/resources/{nice_id.lower()}-pdf-"
        try:
            # First, get the guidance page to find PDF link
            page_url = f"{self.NICE_API}/guidance/{nice_id.lower()}"
            resp = SESSION.get(page_url, timeout=15)
            if resp.status_code != 200:
                log.warning("NICE %s: page not found (status=%d)", nice_id, resp.status_code)
                return None

            # Try direct PDF download (NICE often uses predictable URLs)
            # The actual URL varies, try the common pattern
            base = f"{self.NICE_API}/guidance/{nice_id.lower()}/pdf"
            resp2 = SESSION.get(base, timeout=30, allow_redirects=True)
            if resp2.status_code == 200 and "pdf" in resp2.headers.get("content-type", "").lower():
                filepath = output_dir / f"NICE-{nice_id}.pdf"
                filepath.write_bytes(resp2.content)
                log.info("Downloaded NICE: %s (%d bytes)", nice_id, len(resp2.content))
                return filepath
            log.warning("NICE %s: PDF not directly accessible", nice_id)
            return None
        except Exception as e:
            log.error("NICE download failed %s: %s", nice_id, e)
            return None


# ─── WHO Downloader ─────────────────────────────────────────────────────────

class WHODownloader:
    """Download WHO guidelines from IRIS repository."""

    def download(self, isbn: str, output_dir: Path) -> Path | None:
        """Download WHO publication by ISBN."""
        output_dir.mkdir(parents=True, exist_ok=True)
        url = f"https://apps.who.int/iris/bitstream/handle/10665/{isbn}"
        try:
            resp = SESSION.get(url, timeout=30, allow_redirects=True)
            if resp.status_code == 200:
                filepath = output_dir / f"WHO-{isbn}.pdf"
                filepath.write_bytes(resp.content)
                log.info("Downloaded WHO: %s (%d bytes)", isbn, len(resp.content))
                return filepath
            log.warning("WHO %s: not accessible", isbn)
            return None
        except Exception as e:
            log.error("WHO download failed %s: %s", isbn, e)
            return None


# ─── Main Orchestrator ──────────────────────────────────────────────────────

class StandardsDownloader:
    """Main orchestrator for downloading medical standards."""

    def __init__(self, output_dir: Path = OUTPUT_DIR):
        self.output_dir = output_dir
        self.manifest: list[Standard] = []
        self.pubmed = None
        self.nice = NICEDownloader()
        self.who = WHODownloader()
        if BIOPYTHON_AVAILABLE:
            self.pubmed = PubMedDownloader()

    def load_manifest(self, standards: list[Standard]):
        self.manifest = standards

    def download_all(self):
        """Download all standards from manifest."""
        results = {"success": [], "failed": [], "skipped": []}

        for std in self.manifest:
            log.info("--- Processing: %s [%s] ---", std.id, std.source)
            filepath = None

            if std.source == "pubmed":
                filepath = self._download_pubmed(std)
            elif std.source == "nice":
                filepath = self.nice.get_guideline_pdf(std.source_id or std.url.split("/")[-1], self.output_dir / "nice")
            elif std.source == "who":
                filepath = self._download_who(std)
            elif std.source in ("nmpa", "cdc", "hl7", "iso", "iec"):
                filepath = self._download_webpage(std)

            if filepath:
                std.downloaded = True
                std.local_path = str(filepath)
                results["success"].append(std.id)
            elif std.source in ("iso", "iec", "snomed", "loinc"):
                results["skipped"].append((std.id, "copyright restricted, URL saved"))
            else:
                results["failed"].append(std.id)

            time.sleep(0.5)  # Rate limiting

        self._save_manifest()
        return results

    def _download_pubmed(self, std: Standard) -> Path | None:
        if not self.pubmed:
            return None
        pmids = self.pubmed.search(std.title, max_results=3)
        if not pmids:
            return None
        articles = self.pubmed.get_details(pmids)
        for art in articles:
            if art["has_pmc"]:
                return self.pubmed.download_pmc(art["pmcid"], self.output_dir / "pubmed")
        # Save metadata even if no full text
        meta_path = self.output_dir / "pubmed" / f"{std.id}-metadata.json"
        meta_path.parent.mkdir(parents=True, exist_ok=True)
        meta_path.write_text(json.dumps(articles, indent=2, ensure_ascii=False), encoding="utf-8")
        return meta_path

    def _download_who(self, std: Standard) -> Path | None:
        # Extract WHO document number from URL
        parts = std.url.rstrip("/").split("/")
        doc_id = parts[-1] if parts else std.source_id
        return self.who.download(doc_id, self.output_dir / "who")

    def _download_webpage(self, std: Standard) -> Path | None:
        """Save webpage as reference (for standards that aren't directly downloadable)."""
        output_dir = self.output_dir / std.source
        output_dir.mkdir(parents=True, exist_ok=True)
        try:
            resp = SESSION.get(std.url, timeout=15, allow_redirects=True)
            filepath = output_dir / f"{std.id}.html"
            filepath.write_text(f"""<!-- Saved from: {std.url} -->
<h1>{std.title}</h1>
<p>Source URL: <a href="{std.url}">{std.url}</a></p>
<p>Category: {std.category} | Priority: {std.priority}</p>
<hr>
{resp.text[:50000]}
""", encoding="utf-8")
            log.info("Saved webpage: %s", std.id)
            return filepath
        except Exception as e:
            log.error("Webpage save failed %s: %s", std.id, e)
            # Save minimal placeholder
            filepath = output_dir / f"{std.id}-meta.json"
            filepath.write_text(json.dumps({
                "id": std.id, "title": std.title, "url": std.url,
                "status": "url_saved", "note": "Not downloadable - see URL"
            }, indent=2, ensure_ascii=False), encoding="utf-8")
            return filepath

    def _save_manifest(self):
        """Save download manifest with results."""
        manifest_path = self.output_dir / "download-manifest.json"
        data = {
            "generated": datetime.now().isoformat(),
            "standards": [
                {
                    "id": s.id, "title": s.title, "title_cn": s.title_cn,
                    "source": s.source, "url": s.url, "category": s.category,
                    "specialty": s.specialty, "priority": s.priority,
                    "downloaded": s.downloaded, "local_path": s.local_path,
                }
                for s in self.manifest
            ]
        }
        manifest_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        log.info("Manifest saved: %s", manifest_path)

    def print_summary(self, results: dict):
        """Print download summary."""
        print("\n" + "=" * 70)
        print("  XHAIP Medical Standards Download Report")
        print("=" * 70)
        print(f"  Total standards:      {len(self.manifest)}")
        print(f"  Successfully downloaded: {len(results['success'])}")
        print(f"  Failed:                 {len(results['failed'])}")
        print(f"  Skipped (copyright):    {len(results['skipped'])}")
        print(f"  Output directory:       {self.output_dir.absolute()}")
        print("=" * 70)

        if results["failed"]:
            print("\n  Failed (may need manual download):")
            for fid in results["failed"]:
                std = next((s for s in self.manifest if s.id == fid), None)
                if std:
                    print(f"    - {std.id}: {std.url}")

        if results["skipped"]:
            print("\n  Skipped (copyright/proprietary - URL saved for reference):")
            for sid, note in results["skipped"]:
                std = next((s for s in self.manifest if s.id == sid), None)
                if std:
                    print(f"    - {std.id}: {std.url} ({note})")

        print(f"\n  Manifest: {self.output_dir / 'download-manifest.json'}")
        print(f"  Run 'python {__file__} --list' to view all standards")


# ─── CLI ────────────────────────────────────────────────────────────────────

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Download medical standards and guidelines")
    parser.add_argument("--all", action="store_true", help="Download all priority standards")
    parser.add_argument("--list", action="store_true", help="List available standards")
    parser.add_argument("--search", type=str, help="Search PubMed for guidelines on a topic")
    parser.add_argument("--source", choices=["pubmed", "nice", "who", "cdc", "nmpa"], help="Filter by source")
    parser.add_argument("--output", type=str, default=str(OUTPUT_DIR), help="Output directory")
    parser.add_argument("--max", type=int, default=5, help="Max search results")

    args = parser.parse_args()
    output_dir = Path(args.output)

    downloader = StandardsDownloader(output_dir)

    if args.list:
        print(f"\nAvailable priority standards ({len(PRIORITY_STANDARDS)}):\n")
        for s in PRIORITY_STANDARDS:
            print(f"  [{s.priority}] {s.id}")
            print(f"    Title: {s.title}")
            print(f"    Source: {s.source} | Category: {s.category}")
            if s.url:
                print(f"    URL: {s.url}")
            print()
        return

    if args.search:
        if not BIOPYTHON_AVAILABLE:
            print("PubMed search requires: pip install biopython")
            return
        pm = PubMedDownloader()
        pmids = pm.search(args.search, max_results=args.max)
        if pmids:
            articles = pm.get_details(pmids)
            for art in articles:
                print(f"  PMID:{art['pmid']} {art['title'][:80]}... ({art['journal']}, {art['year']})")
                if art["has_pmc"]:
                    print(f"    -> Full text available via PMC:{art['pmcid']}")
        else:
            print("No results found.")
        return

    if args.all or args.source:
        standards = PRIORITY_STANDARDS
        if args.source:
            standards = [s for s in standards if s.source == args.source]
        downloader.load_manifest(standards)
        results = downloader.download_all()
        downloader.print_summary(results)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
