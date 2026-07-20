import json
from io import BytesIO
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
from reportlab.pdfgen import canvas

# Define Premium Color Palette (matching Nyaya AI design tokens)
COLOR_PRIMARY = HexColor("#733635")      # Crimson/Garnet
COLOR_SECONDARY = HexColor("#8C4E4F")    # Muted Copper
COLOR_DARK = HexColor("#351E1C")         # Black Kite
COLOR_LIGHT_BG = HexColor("#F5F4ED")     # Morning Snow
COLOR_WHITE = HexColor("#FFFFFF")
COLOR_BORDER = HexColor("#E2E2D5")
COLOR_RISK_HIGH = HexColor("#FF6037")    # Toxic Orange (text label)
COLOR_GREEN = HexColor("#385723")        # Safe Text

class NumberedCanvas(canvas.Canvas):
    """Canvas that computes total pages dynamically for a running footer."""
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
            self.draw_page_elements(num_pages)
            super().showPage()
        super().save()

    def draw_page_elements(self, page_count):
        self.saveState()
        
        # Draw running header (on pages > 1)
        if self._pageNumber > 1:
            self.setFont("Helvetica", 8)
            self.setFillColor(COLOR_SECONDARY)
            self.drawString(54, 750, "Nyaya AI — Legal Audit Compliance Report")
            self.setStrokeColor(COLOR_BORDER)
            self.setLineWidth(0.5)
            self.line(54, 742, letter[0] - 54, 742)

        # Draw running footer (on all pages)
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(COLOR_DARK)
        self.drawString(54, 36, "Nyaya AI")
        self.setFont("Helvetica", 8)
        self.setFillColor(COLOR_SECONDARY)
        self.drawString(100, 36, "· Grounded in Gazette of India")
        
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(letter[0] - 54, 36, page_str)
        self.restoreState()


def generate_pdf_report(scan_record) -> bytes:
    """Generates a highly-stylized compliance report PDF from a ScanRecord in-memory."""
    # Parse results from database
    results = {}
    if scan_record.results_json:
        try:
            results = json.loads(scan_record.results_json)
        except Exception:
            pass

    findings = results.get("findings", [])
    contract_name = scan_record.contract_name
    scan_date_str = scan_record.scan_date.strftime("%B %d, %Y at %I:%M %p")
    status = results.get("status", scan_record.status)
    scan_confidence = results.get("scan_confidence", 0.0)

    # Initialize PDF document
    pdf_buffer = BytesIO()
    doc = SimpleDocTemplate(
        pdf_buffer,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54
    )

    # Styles Setup
    styles = getSampleStyleSheet()
    
    # Custom Typography Styles
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=22,
        leading=26,
        textColor=COLOR_PRIMARY,
        spaceAfter=6
    )
    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=COLOR_SECONDARY,
        spaceAfter=15
    )
    heading_style = ParagraphStyle(
        "DocHeading",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=17,
        textColor=COLOR_PRIMARY,
        spaceBefore=12,
        spaceAfter=8,
        keepWithNext=True
    )
    body_style = ParagraphStyle(
        "DocBody",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=14,
        textColor=COLOR_DARK,
        spaceAfter=6
    )
    meta_label_style = ParagraphStyle(
        "MetaLabel",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=12,
        textColor=COLOR_PRIMARY
    )
    meta_value_style = ParagraphStyle(
        "MetaValue",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=COLOR_DARK
    )
    clause_text_style = ParagraphStyle(
        "ClauseText",
        parent=styles["Normal"],
        fontName="Courier-Oblique" if status == "ocr_required" else "Helvetica-Oblique",
        fontSize=8.5,
        leading=12,
        textColor=COLOR_SECONDARY
    )
    tag_high_style = ParagraphStyle(
        "TagHigh",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=10,
        textColor=COLOR_RISK_HIGH
    )
    tag_med_style = ParagraphStyle(
        "TagMed",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=10,
        textColor=COLOR_SECONDARY
    )

    story = []

    # 1. HEADER TITLE
    story.append(Paragraph("Nyaya AI Compliance Report", title_style))
    story.append(Paragraph("Indian Legal Contract Intelligence Audit & Statutory Alignment", subtitle_style))
    story.append(Spacer(1, 5))

    # 2. METADATA SUMMARY TABLE
    status_mapping = {
        "risks_found": "RISKS FOUND",
        "no_material_risks_found": "COMPLIANT",
        "insufficient_evidence": "INSUFFICIENT EVIDENCE",
        "ocr_required": "OCR REQUIRED",
    }
    status_text = status_mapping.get(status, status.upper())
    
    overall_risk_text = (scan_record.risk_level or "None").upper()

    summary_data = [
        [
            Paragraph("Contract Name:", meta_label_style),
            Paragraph(contract_name, meta_value_style),
            Paragraph("Scan Date:", meta_label_style),
            Paragraph(scan_date_str, meta_value_style)
        ],
        [
            Paragraph("Scan Status:", meta_label_style),
            Paragraph(status_text, meta_value_style),
            Paragraph("Overall Risk Level:", meta_label_style),
            Paragraph(overall_risk_text, meta_value_style)
        ],
        [
            Paragraph("Total Clauses Scanned:", meta_label_style),
            Paragraph(str(scan_record.clause_count), meta_value_style),
            Paragraph("Scan Confidence:", meta_label_style),
            Paragraph(f"{scan_confidence * 100:.1f}%", meta_value_style)
        ]
    ]
    
    summary_table = Table(summary_data, colWidths=[130, 130, 110, 134])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), COLOR_LIGHT_BG),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('BOX', (0, 0), (-1, -1), 1, COLOR_SECONDARY),
        ('LINEBELOW', (0, 0), (-1, -2), 0.5, COLOR_BORDER),
    ]))
    
    story.append(summary_table)
    story.append(Spacer(1, 20))

    # 3. SCAN COMPLIANCE SUMMARY PARAGRAPH
    story.append(Paragraph("Executive Summary", heading_style))
    summary_message = results.get("message", "Scan complete.")
    story.append(Paragraph(summary_message, body_style))
    story.append(Spacer(1, 15))

    # 4. DETAILED FINDINGS LIST
    story.append(Paragraph("Identified Risks & statutory Violations", heading_style))
    
    if not findings:
        if status == "ocr_required":
            story.append(Paragraph("<b>No analysis available:</b> This document appears to be scanned or contains image-only pages. Optical Character Recognition (OCR) must be run locally on this contract to parse and analyze its clauses.", body_style))
        else:
            story.append(Paragraph("<b>No material statutory conflicts detected:</b> The contract clauses successfully aligned with our indexed compliance engines (Indian Contract Act, MSMED Act, DPDP Act, IT Act, etc.).", body_style))
    else:
        for idx, finding in enumerate(findings, 1):
            finding_story = []
            
            # Heading for the individual finding card
            clause_type_lbl = (finding.get("clause_type") or "Clause").replace("_", " ").title()
            title_text = f"Finding {idx}: {clause_type_lbl} (Clause {finding.get('clause_number', '?')} on Page {finding.get('page', 0)})"
            
            # Risk tag coloring
            risk = finding.get("risk_level", "medium").lower()
            if risk == "high":
                tag_para = Paragraph("<b>[HIGH RISK / VOID]</b>", tag_high_style)
            else:
                tag_para = Paragraph("<b>[MEDIUM RISK / REVIEW]</b>", tag_med_style)
                
            heading_table = Table([[Paragraph(title_text, heading_style), tag_para]], colWidths=[380, 124])
            heading_table.setStyle(TableStyle([
                ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
                ('VALIGN', (0, 0), (-1, -1), 'BOTTOM'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ]))
            finding_story.append(heading_table)
            
            # Contract Text Block (indented Courier box)
            contract_box_data = [[
                Paragraph(f"Contract Clause Text:<br/><i>\"{finding.get('clause_text', '').strip()}\"</i>", clause_text_style)
            ]]
            contract_box_table = Table(contract_box_data, colWidths=[504])
            contract_box_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), COLOR_LIGHT_BG),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('LEFTPADDING', (0, 0), (-1, -1), 10),
                ('RIGHTPADDING', (0, 0), (-1, -1), 10),
                ('BOX', (0, 0), (-1, -1), 0.5, COLOR_BORDER),
            ]))
            finding_story.append(contract_box_table)
            finding_story.append(Spacer(1, 6))

            # Violated Statute Title
            statute_info = f"<b>Conflicting Indian Statute:</b> {finding.get('conflicting_act', '')}, Section {finding.get('conflicting_section', '')}"
            finding_story.append(Paragraph(statute_info, body_style))

            # Grounded Quote
            statute_quote = f"<b>Official Statutory Quote:</b><br/><i>\"{finding.get('conflicting_law_quote', '').strip()}\"</i>"
            finding_story.append(Paragraph(statute_quote, body_style))

            # Explanation
            explanation_info = f"<b>Legal Analysis:</b> {finding.get('explanation', '')}"
            finding_story.append(Paragraph(explanation_info, body_style))

            # Recommendation
            recommendation_info = f"<b>Actionable Mitigation Stance:</b> {finding.get('recommended_action', '')}"
            finding_story.append(Paragraph(recommendation_info, body_style))
            
            finding_story.append(Spacer(1, 15))
            
            # Add keeping them together to prevent orphan headers at page breaks
            story.append(KeepTogether(finding_story))

    # Build the document using our custom NumberedCanvas
    doc.build(story, canvasmaker=NumberedCanvas)
    
    pdf_bytes = pdf_buffer.getvalue()
    pdf_buffer.close()
    return pdf_bytes
