"""Generate a clean, beautifully formatted, to-the-point PDF report for PEC 4 DevOps FA2 Activity."""

import os
import sys
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    KeepTogether,
    HRFlowable,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas


class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas to dynamically compute and print total page count."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748B"))

        # Header (Pages 2+)
        if self._pageNumber > 1:
            self.drawString(
                40,
                letter[1] - 30,
                "ResearchOps AI — DevOps FA2 Engineering Report (Units 3 & 4)",
            )
            self.setStrokeColor(colors.HexColor("#CBD5E1"))
            self.setLineWidth(0.5)
            self.line(40, letter[1] - 34, letter[0] - 40, letter[1] - 34)

        # Footer (All pages)
        self.setStrokeColor(colors.HexColor("#E2E8F0"))
        self.setLineWidth(0.5)
        self.line(40, 36, letter[0] - 40, 36)

        footer_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(letter[0] - 40, 24, footer_text)
        self.drawString(
            40,
            24,
            "PEC 4 - DevOps (7th Sem) | Repository: Niruuu2005/ResearchHUB | FA2 Evaluation",
        )
        self.restoreState()


def build_pdf(filename="docs/ResearchOps_DevOps_FA2_Guide.pdf"):
    os.makedirs(os.path.dirname(filename), exist_ok=True)

    # Document setup: 40pt margins (~0.55 in)
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        leftMargin=40,
        rightMargin=40,
        topMargin=46,
        bottomMargin=46,
    )

    styles = getSampleStyleSheet()

    # Custom Color Palette
    PRIMARY = colors.HexColor("#0F172A")  # Slate 900
    ACCENT = colors.HexColor("#1D4ED8")   # Blue 700
    TEXT_DARK = colors.HexColor("#1E293B")# Slate 800
    MUTED = colors.HexColor("#64748B")    # Slate 500
    BG_LIGHT = colors.HexColor("#F8FAFC") # Slate 50
    BORDER_COL = colors.HexColor("#E2E8F0")

    # Typography Styles
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=PRIMARY,
        spaceAfter=4,
    )

    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=13,
        textColor=MUTED,
        spaceAfter=10,
    )

    h1_style = ParagraphStyle(
        "SectionH1",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=15,
        textColor=PRIMARY,
        spaceBefore=10,
        spaceAfter=5,
        keepWithNext=True,
    )

    h2_style = ParagraphStyle(
        "SectionH2",
        parent=styles["Heading3"],
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=13,
        textColor=ACCENT,
        spaceBefore=7,
        spaceAfter=3,
        keepWithNext=True,
    )

    body_style = ParagraphStyle(
        "BodyDark",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11.5,
        textColor=TEXT_DARK,
        spaceAfter=5,
    )

    bullet_style = ParagraphStyle(
        "BulletText",
        parent=body_style,
        leftIndent=12,
        firstLineIndent=-8,
        spaceAfter=3,
    )

    code_style = ParagraphStyle(
        "CodeStyle",
        parent=styles["Normal"],
        fontName="Courier",
        fontSize=7.5,
        leading=9.5,
        textColor=colors.HexColor("#0F172A"),
    )

    table_header_style = ParagraphStyle(
        "TableHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=colors.white,
    )

    table_cell_style = ParagraphStyle(
        "TableCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7.8,
        leading=10,
        textColor=TEXT_DARK,
    )

    table_cell_bold = ParagraphStyle(
        "TableCellBold",
        parent=table_cell_style,
        fontName="Helvetica-Bold",
    )

    story = []

    # ==================== HEADER BLOCK ====================
    story.append(Paragraph("ResearchOps AI — DevOps FA2 Engineering Report", title_style))
    story.append(
        Paragraph(
            "<b>Course:</b> PEC 4 - DevOps (Units 3 & 4) &nbsp;|&nbsp; "
            "<b>Evaluation:</b> FA2 Activity (10 Marks) &nbsp;|&nbsp; "
            "<b>Target:</b> October 2026",
            subtitle_style,
        )
    )
    story.append(HRFlowable(width="100%", thickness=1.5, color=ACCENT, spaceAfter=8))

    # ==================== SECTION 1: OVERVIEW & ARCHITECTURE ====================
    story.append(Paragraph("1. Project Overview & Working", h1_style))
    story.append(
        Paragraph(
            "<b>ResearchOps AI</b> is an asynchronous literature intelligence microservice and DevOps platform. "
            "It solves the real-world problem of scattered academic research by concurrently querying three open-access registries "
            "(<b>Wikipedia</b>, <b>OpenAlex</b>, and <b>Crossref</b>), automatically deduplicating DOIs, and providing grounded RAG "
            "literature review generation, while running on an observable, resilient microservice architecture.",
            body_style,
        )
    )

    story.append(Paragraph("<b>End-to-End Workflow:</b>", h2_style))
    story.append(
        Paragraph(
            "• <b>1. User Query:</b> User submits a topic (e.g. <i>'Quantum Computing'</i>) via the Single-Page Web UI.<br/>"
            "• <b>2. Async Aggregation:</b> FastAPI initiates concurrent <code>httpx</code> queries via <code>asyncio.gather</code> to Wikipedia, OpenAlex, and Crossref.<br/>"
            "• <b>3. Deduplication & Synthesis:</b> Normalizes DOIs and publication titles across registries, eliminating duplicate citations.<br/>"
            "• <b>4. State & Background Jobs:</b> Results persist in <b>PostgreSQL 16</b>, are cached in <b>Redis 7</b>, and heavy PDF chunking runs via <b>Celery</b>.<br/>"
            "• <b>5. SRE Telemetry:</b> Every request live-updates custom <b>Prometheus</b> counters and gauges (latency, traffic, errors, saturation).",
            bullet_style,
        )
    )
    story.append(Spacer(1, 4))

    # Microservices Summary Table
    story.append(Paragraph("<b>Microservice Architecture Topology:</b>", h2_style))
    arch_data = [
        [
            Paragraph("Service", table_header_style),
            Paragraph("Technology", table_header_style),
            Paragraph("Role & Responsibilities", table_header_style),
            Paragraph("Port", table_header_style),
        ],
        [
            Paragraph("<b>API</b>", table_cell_bold),
            Paragraph("FastAPI (Python 3.12)", table_cell_style),
            Paragraph("Core REST API, async provider orchestrator, endpoints (/research, /health, /metrics)", table_cell_style),
            Paragraph("8000", table_cell_style),
        ],
        [
            Paragraph("<b>Worker</b>", table_cell_bold),
            Paragraph("Celery + Redis", table_cell_style),
            Paragraph("Asynchronous document parsing, PDF chunking, 384-dim dense embeddings", table_cell_style),
            Paragraph("Internal", table_cell_style),
        ],
        [
            Paragraph("<b>Database</b>", table_cell_bold),
            Paragraph("PostgreSQL 16 (pgvector)", table_cell_style),
            Paragraph("Relational store for saved research, projects, chats, and audit logs", table_cell_style),
            Paragraph("5432", table_cell_style),
        ],
        [
            Paragraph("<b>Broker</b>", table_cell_bold),
            Paragraph("Redis 7 Alpine", table_cell_style),
            Paragraph("In-memory task broker and caching layer coordinating async jobs", table_cell_style),
            Paragraph("6379", table_cell_style),
        ],
        [
            Paragraph("<b>Prometheus</b>", table_cell_bold),
            Paragraph("Prometheus v2.51", table_cell_style),
            Paragraph("Scrapes /metrics every 15s; evaluates provider latency and saturation", table_cell_style),
            Paragraph("9090", table_cell_style),
        ],
        [
            Paragraph("<b>Grafana</b>", table_cell_bold),
            Paragraph("Grafana v10.4", table_cell_style),
            Paragraph("Visual telemetry dashboard tracking the 4 Golden Signals and SLO dials", table_cell_style),
            Paragraph("3001", table_cell_style),
        ],
        [
            Paragraph("<b>Gateway</b>", table_cell_bold),
            Paragraph("Nginx Alpine", table_cell_style),
            Paragraph("Reverse proxy gateway routing traffic to API and frontend assets", table_cell_style),
            Paragraph("8080", table_cell_style),
        ],
    ]

    arch_table = Table(arch_data, colWidths=[65, 110, 310, 47])
    arch_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("GRID", (0, 0), (-1, -1), 0.5, BORDER_COL),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [colors.white, BG_LIGHT],
                ),
            ]
        )
    )
    story.append(arch_table)
    story.append(Spacer(1, 8))

    # ==================== SECTION 2: DEVOPS IMPLEMENTATION ====================
    story.append(Paragraph("2. DevOps Implementation Breakdown (Units 3 & 4)", h1_style))
    story.append(
        Paragraph(
            "Below is the exact engineering breakdown of how and why each DevOps stage is implemented in this codebase:",
            body_style,
        )
    )

    devops_stages = [
        (
            "1. Source Code & Quality Gates (Git, Ruff, Pytest)",
            "<b>Why:</b> Guarantees zero code regressions, enforces clean code hygiene, and validates endpoint contracts.<br/>"
            "<b>How:</b> Configured <code>ruff</code> linter for instant linting; authored <b>35 automated tests</b> in <code>tests/</code> "
            "covering health probes, provider fallback mocking, deduplication logic, and Prometheus metrics formatting.<br/>"
            "<b>Command:</b> <code>ruff check app tests</code> &nbsp;|&nbsp; <code>pytest -v --cov=app</code>",
        ),
        (
            "2. Continuous Integration (GitHub Actions)",
            "<b>Why:</b> Eliminates manual testing. Every commit is tested and verified on a clean Ubuntu runner in the cloud.<br/>"
            "<b>How:</b> Workflow in <code>.github/workflows/ci.yml</code> runs on push/PR. Stages: (1) Setup Python 3.12 with pip cache; "
            "(2) Ruff static analysis; (3) Pytest suite (all 35 tests must pass); (4) Docker Buildx building both API and Worker images.<br/>"
            "<b>Status:</b> Automated green checkmark on GitHub on every commit.",
        ),
        (
            "3. Containerization (Docker & Multi-Stage Builds)",
            "<b>Why:</b> Solves environment drift and guarantees identical behavior across developer laptops, cloud, and Kubernetes.<br/>"
            "<b>How:</b> <code>Dockerfile</code> uses <code>python:3.12-slim</code> base (~200MB), runs as non-root user <code>appuser</code> "
            "for security hardening, and embeds an internal <code>HEALTHCHECK</code> probing <code>/health</code>.<br/>"
            "<b>Command:</b> <code>docker build -t researchops-api:latest .</code>",
        ),
        (
            "4. Multi-Container Orchestration (Docker Compose)",
            "<b>Why:</b> Spins up the full 6-service microservice stack locally with a single command without port clashes.<br/>"
            "<b>How:</b> <code>docker-compose.yml</code> connects API, Worker, PostgreSQL, Redis, Prometheus, Grafana, and Nginx on an "
            "internal bridge network with named volumes (<code>pg_data</code>, <code>redis_data</code>, <code>prom_data</code>).<br/>"
            "<b>Command:</b> <code>docker compose up --build -d</code> &nbsp;|&nbsp; <code>docker compose ps</code>",
        ),
        (
            "5. Infrastructure as Code (Terraform on AWS)",
            "<b>Why:</b> Eliminates error-prone manual cloud console clicking; infrastructure is version-controlled and reproducible.<br/>"
            "<b>How:</b> <code>terraform/main.tf</code> provisions an AWS EC2 instance (Ubuntu 22.04 LTS) and Security Group opening ports "
            "22, 80, 8000, 9090, and 3001, outputting the public IP automatically.<br/>"
            "<b>Command:</b> <code>cd terraform && terraform init && terraform plan && terraform apply</code>",
        ),
        (
            "6. Configuration Management (Ansible)",
            "<b>Why:</b> Connects to the raw EC2 instance over SSH and turns it into a running platform with zero manual SSH commands.<br/>"
            "<b>How:</b> <code>ansible/deploy.yml</code> updates OS packages, installs Docker Engine & Compose, clones repository to "
            "<code>/opt/researchhub</code>, templates <code>.env</code>, and runs <code>docker compose up -d</code>.<br/>"
            "<b>Command:</b> <code>ansible-playbook -i ansible/inventory.ini ansible/deploy.yml</code>",
        ),
        (
            "7. Production Container Orchestration (Kubernetes & Kustomize)",
            "<b>Why:</b> Enterprise high availability, zero-downtime rolling updates, self-healing pods, and autoscaling.<br/>"
            "<b>How:</b> Suite of 11 manifests in <code>k8s/</code>: Namespace, ConfigMap, Secret, StatefulSets for Postgres & Redis with PVCs, "
            "Deployment with 2 replicas and <code>RollingUpdate</code> (<code>maxSurge: 1, maxUnavailable: 0</code>), Ingress routing, and "
            "<b>HPA</b> scaling pods up to 8 replicas when CPU exceeds 70%. Bundled with <code>kustomization.yaml</code>.<br/>"
            "<b>Command:</b> <code>kubectl apply --dry-run=client -k k8s/</code> &nbsp;|&nbsp; <code>kubectl apply -k k8s/</code>",
        ),
        (
            "8. Monitoring, Observability & SRE (Prometheus & Grafana - Unit 4)",
            "<b>Why:</b> Adheres to Google SRE principles: monitoring health before users complain, measuring Golden Signals and SLOs.<br/>"
            "<b>How:</b> Implemented distinct <code>/health</code> (Liveness) and <code>/ready</code> (Readiness) probes. Exposes custom "
            "<code>/metrics</code> in Prometheus exposition format. Tracks probe latencies for OpenAlex, Wikipedia, and Crossref. "
            "Grafana dashboard auto-provisioned at port 3001. Enforces <b>99.5% availability SLO</b>.<br/>"
            "<b>Command:</b> <code>curl http://localhost:8000/metrics</code> &nbsp;|&nbsp; <code>http://localhost:3001</code>",
        ),
    ]

    for title, desc in devops_stages:
        story.append(Paragraph(title, h2_style))
        story.append(Paragraph(desc, body_style))
        story.append(Spacer(1, 2))

    story.append(Spacer(1, 4))

    # ==================== SECTION 3: SRE & 4 GOLDEN SIGNALS TABLE ====================
    story.append(Paragraph("3. SRE Framework: 4 Golden Signals & SLO Alignment", h1_style))
    sre_data = [
        [
            Paragraph("Golden Signal", table_header_style),
            Paragraph("Implemented Metric / Probe", table_header_style),
            Paragraph("Engineering Purpose", table_header_style),
            Paragraph("Target SLO / Threshold", table_header_style),
        ],
        [
            Paragraph("<b>1. Latency</b>", table_cell_bold),
            Paragraph("<code>researchops_provider_latency_ms</code>", table_cell_style),
            Paragraph("Measures real-time response times of OpenAlex, Wikipedia, and Crossref probes.", table_cell_style),
            Paragraph("p95 &lt; 1500 ms", table_cell_style),
        ],
        [
            Paragraph("<b>2. Traffic</b>", table_cell_bold),
            Paragraph("<code>researchops_total_papers</code><br/><code>researchops_total_projects</code>", table_cell_style),
            Paragraph("Measures active system usage demand, database throughput, and saved literature items.", table_cell_style),
            Paragraph("&gt; 100 concurrent reqs", table_cell_style),
        ],
        [
            Paragraph("<b>3. Errors</b>", table_cell_bold),
            Paragraph("Probe degradation status & HTTP 5xx tracking", table_cell_style),
            Paragraph("Tracks rate of requests that fail or encounter third-party upstream API timeouts.", table_cell_style),
            Paragraph("&lt; 0.5% failure rate (99.5% uptime SLO)", table_cell_style),
        ],
        [
            Paragraph("<b>4. Saturation</b>", table_cell_bold),
            Paragraph("<code>researchops_active_background_jobs</code>", table_cell_style),
            Paragraph("Monitors Celery worker queue depth, CPU limits, and DB connection pool saturation.", table_cell_style),
            Paragraph("Queue depth &lt; 20<br/>CPU &lt; 70%", table_cell_style),
        ],
    ]

    sre_table = Table(sre_data, colWidths=[75, 145, 205, 105])
    sre_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("GRID", (0, 0), (-1, -1), 0.5, BORDER_COL),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [colors.white, BG_LIGHT],
                ),
            ]
        )
    )
    story.append(sre_table)
    story.append(Spacer(1, 8))

    # ==================== SECTION 4: MASTER VIVA QUESTIONS ====================
    story.append(Paragraph("4. Faculty Viva Defense — Top 5 Questions & Crisp Answers", h1_style))
    viva_qa = [
        (
            "Q1: Why did you separate /health (Liveness) and /ready (Readiness) probes?",
            "<b>Answer:</b> A Liveness probe checks if the Python/FastAPI process is executing; if it fails, the orchestrator "
            "(Kubernetes/Docker) restarts the pod. A Readiness probe verifies that downstream dependencies (PostgreSQL and Redis) "
            "are connected. If the DB is saturated, the readiness probe fails, instructing Kubernetes to temporarily stop routing "
            "incoming traffic to that pod without needlessly killing and restarting the process.",
        ),
        (
            "Q2: How does your project implement Unit 4 SRE Golden Signals?",
            "<b>Answer:</b> We expose custom metrics in <code>/metrics</code>: (1) <b>Latency</b> via provider probe latencies; "
            "(2) <b>Traffic</b> via total projects/papers; (3) <b>Errors</b> via probe degradation status; and (4) <b>Saturation</b> "
            "via Celery background job queue depth and database connection counts.",
        ),
        (
            "Q3: What is the architectural distinction between Terraform and Ansible?",
            "<b>Answer:</b> Terraform is our <i>Infrastructure as Code (IaC)</i> tool that provisions the AWS virtual machine and "
            "security firewall rules. Ansible is our <i>Configuration Management</i> tool that SSH-connects to that VM to install "
            "Docker, configure environment secrets, and launch the multi-service container cluster.",
        ),
        (
            "Q4: How does Kubernetes guarantee zero-downtime deployments in your manifests?",
            "<b>Answer:</b> In <code>k8s/05-api-deployment.yaml</code>, we enforce a <code>RollingUpdate</code> strategy with "
            "<code>maxSurge: 1</code> and <code>maxUnavailable: 0</code>. Kubernetes spins up a new pod, waits for its readiness probe "
            "to return healthy, and only then tears down the old replica.",
        ),
        (
            "Q5: How does the system handle an external provider outage (e.g. Crossref or Wikipedia down)?",
            "<b>Answer:</b> The orchestrator executes parallel async calls with <code>asyncio.gather(..., return_exceptions=True)</code>. "
            "If an external API times out, it is caught gracefully: the user receives partial synthesized results with a warning badge, "
            "Prometheus records degraded status, and the application never crashes.",
        ),
    ]

    for q, a in viva_qa:
        story.append(Paragraph(f"<b>{q}</b>", h2_style))
        story.append(Paragraph(a, body_style))
        story.append(Spacer(1, 2))

    story.append(Spacer(1, 6))

    # ==================== SECTION 5: COMMAND CHEAT SHEET ====================
    story.append(Paragraph("5. Quick Verification Commands", h1_style))
    cmd_data = [
        [
            Paragraph("Verification Step", table_header_style),
            Paragraph("Command to Execute", table_header_style),
            Paragraph("Expected Result", table_header_style),
        ],
        [
            Paragraph("1. Code Linter", table_cell_bold),
            Paragraph("<code>ruff check app tests</code>", code_style),
            Paragraph("0 errors / clean code hygiene", table_cell_style),
        ],
        [
            Paragraph("2. Test Suite", table_cell_bold),
            Paragraph("<code>pytest -v --cov=app</code>", code_style),
            Paragraph("35 / 35 tests passed in ~8 seconds", table_cell_style),
        ],
        [
            Paragraph("3. Full Local Stack", table_cell_bold),
            Paragraph("<code>docker compose up --build -d</code>", code_style),
            Paragraph("All 6 microservices running and healthy", table_cell_style),
        ],
        [
            Paragraph("4. Automated DoD Check", table_cell_bold),
            Paragraph("<code>python scripts/verify_fa2.py</code>", code_style),
            Paragraph("Full green readiness scorecard", table_cell_style),
        ],
        [
            Paragraph("5. K8s Manifest Dry-Run", table_cell_bold),
            Paragraph("<code>kubectl apply --dry-run=client -k k8s/</code>", code_style),
            Paragraph("All 11 manifests pass validation", table_cell_style),
        ],
    ]

    cmd_table = Table(cmd_data, colWidths=[110, 240, 180])
    cmd_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("GRID", (0, 0), (-1, -1), 0.5, BORDER_COL),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [colors.white, BG_LIGHT],
                ),
            ]
        )
    )
    story.append(cmd_table)

    # Build the document
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"[OK] Successfully built PDF report: {filename}")


if __name__ == "__main__":
    out_pdf = "docs/ResearchOps_DevOps_FA2_Guide.pdf"
    if len(sys.argv) > 1:
        out_pdf = sys.argv[1]
    build_pdf(out_pdf)
