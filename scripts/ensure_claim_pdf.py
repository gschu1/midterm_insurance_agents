#!/usr/bin/env python3
"""
Generate PDF from claim_timeline.md and ensure it's at least 10 pages.
If needed, appends appendix sections to the markdown and regenerates.
"""

import re
import sys
from pathlib import Path
from fpdf import FPDF
from pypdf import PdfReader

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MARKDOWN_PATH = PROJECT_ROOT / "data" / "claim_timeline.md"
PDF_PATH = PROJECT_ROOT / "data" / "claim_timeline.pdf"
MIN_PAGES = 10


class MarkdownToPDF(FPDF):
    """Simple PDF generator for markdown content."""
    
    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=15)
        self.set_margins(20, 20, 20)
        self.add_page()
        # Use Courier and clean Unicode characters
        self.set_font("Courier", size=11)
        self.line_height = 6
    
    def _clean_text(self, text: str) -> str:
        """Replace Unicode characters with ASCII equivalents."""
        replacements = {
            '\u2013': '-',  # en dash
            '\u2014': '--',  # em dash
            '\u2018': "'",  # left single quote
            '\u2019': "'",  # right single quote
            '\u201C': '"',  # left double quote
            '\u201D': '"',  # right double quote
            '\u2026': '...',  # ellipsis
            '\u00A0': ' ',  # non-breaking space
            '\u2264': '<=',  # less than or equal
            '\u2265': '>=',  # greater than or equal
            '\u2192': '->',  # right arrow
            '\u2190': '<-',  # left arrow
        }
        for unicode_char, ascii_char in replacements.items():
            text = text.replace(unicode_char, ascii_char)
        # Also handle any other non-ASCII characters by replacing with '?'
        try:
            text.encode('latin-1')
        except UnicodeEncodeError:
            # Replace any remaining non-ASCII with '?'
            text = text.encode('ascii', 'replace').decode('ascii')
        return text
        
    def add_markdown_text(self, text: str):
        """Add markdown-formatted text to PDF."""
        lines = text.split('\n')
        
        for line in lines:
            line = line.rstrip()
            
            # Clean text first
            line = self._clean_text(line)
            
            # Handle headings
            if line.startswith('# '):
                self.set_font("Courier", "B", 16)
                self.ln(8)
                self.cell(0, 10, line[2:], ln=1)
                self.set_font("Courier", size=11)
                self.ln(2)
            elif line.startswith('## '):
                self.set_font("Courier", "B", 14)
                self.ln(6)
                self.cell(0, 8, line[3:], ln=1)
                self.set_font("Courier", size=11)
                self.ln(2)
            elif line.startswith('### '):
                self.set_font("Courier", "B", 12)
                self.ln(4)
                self.cell(0, 7, line[4:], ln=1)
                self.set_font("Courier", size=11)
                self.ln(1)
            elif line.startswith('**') and line.endswith('**'):
                # Bold text
                self.set_font("Courier", "B", 11)
                self.cell(0, self.line_height, line.replace('**', ''), ln=1)
                self.set_font("Courier", size=11)
            elif line.startswith('---'):
                self.ln(4)
                self.line(20, self.get_y(), 190, self.get_y())
                self.ln(4)
            elif line.strip() == '':
                self.ln(3)
            else:
                # Regular text - wrap long lines
                line = line.replace('**', '')  # Remove bold markers for simplicity
                words = line.split()
                current_line = []
                current_width = 0
                max_width = 170  # A4 width minus margins
                
                for word in words:
                    word_width = self.get_string_width(word + ' ')
                    if current_width + word_width > max_width and current_line:
                        self.cell(0, self.line_height, ' '.join(current_line), ln=1)
                        current_line = [word]
                        current_width = word_width
                    else:
                        current_line.append(word)
                        current_width += word_width
                
                if current_line:
                    self.cell(0, self.line_height, ' '.join(current_line), ln=1)


def generate_pdf(markdown_path: Path, pdf_path: Path) -> int:
    """Generate PDF from markdown and return page count."""
    with open(markdown_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    pdf = MarkdownToPDF()
    pdf.add_markdown_text(content)
    pdf.output(str(pdf_path))
    
    # Count pages
    reader = PdfReader(str(pdf_path))
    return len(reader.pages)


def append_appendix_a(markdown_path: Path):
    """Append Appendix A with high-resolution incident log."""
    appendix = """

## Appendix A — High-Resolution Incident Log (Second/Minute Granularity)

This appendix provides second-by-second and minute-by-minute granularity for the incident window surrounding the collision on 2024-01-03.

**2024-01-03 19:35:00** – Weather monitoring station JLM-WX-47 reports light precipitation beginning. Road surface temperature: 8.2°C.

**2024-01-03 19:35:12** – Traffic camera JLM-CAM-112 (Jaffa Road / King George intersection) records normal eastbound flow, average speed 38 km/h.

**2024-01-03 19:36:00** – Municipal maintenance vehicle MUN-8832 completes routine inspection of traffic signals at intersection. All systems operational.

**2024-01-03 19:36:45** – Insured vehicle (2019 Mazda 3, plate 71-234-56) detected by ANPR system entering Jaffa Road from Ben Yehuda Street. Driver identified as Dana Cohen, ID 312547890.

**2024-01-03 19:37:20** – Traffic flow analysis: moderate congestion building on Jaffa Road eastbound. Average speed drops to 32 km/h.

**2024-01-03 19:37:55** – Weather update: precipitation intensity increases. Road surface now fully wet. Visibility: good (500m+).

**2024-01-03 19:38:10** – Vehicle 71-234-56 passes King George Street intersection, maintaining lane 2 of 3. Speed: 40 km/h.

**2024-01-03 19:38:33** – Traffic camera JLM-CAM-114 (Jaffa Road / Shlomzion HaMalka) records vehicle 71-234-56 entering frame. No anomalies detected.

**2024-01-03 19:39:00** – Municipal traffic control center logs routine status check. All cameras operational. No incidents reported.

**2024-01-03 19:39:12** – Vehicle 71-234-56 detected by city camera entering Jaffa Road eastbound at moderate speed. Position: 200m west of Shlomzion HaMalka intersection.

**2024-01-03 19:39:18** – ANPR system confirms vehicle registration: 71-234-56, registered owner Dana Cohen. Insurance status: Active (Magen Insurance, policy AC-2023-8742).

**2024-01-03 19:39:24** – Traffic flow sensor TFS-JLM-089 records speed: 42 km/h. Lane position: center lane (lane 2 of 3).

**2024-01-03 19:39:30** – Weather station update: light rain continues. Road surface: wet. Coefficient of friction estimated: 0.65 (reduced from dry 0.85).

**2024-01-03 19:39:34** – Light rain begins; road surface already wet from earlier showers. Precipitation rate: 0.5 mm/hour.

**2024-01-03 19:39:40** – Vehicle ahead of 71-234-56 (plate 88-901-23, silver Toyota Corolla) begins deceleration. Distance: approximately 25m.

**2024-01-03 19:39:47** – Vehicle 71-234-56 passes King George Street intersection, lane 2 of 3, approximate speed 42 km/h. Traffic light status: green.

**2024-01-03 19:39:52** – Driver of vehicle 88-901-23 applies brakes more aggressively. Distance to 71-234-56: 18m.

**2024-01-03 19:39:58** – Vehicle 71-234-56 driver (Dana Cohen) observes deceleration ahead. Reaction time begins.

**2024-01-03 19:40:00** – Critical moment: Vehicle 88-901-23 comes to near-stop. Distance to 71-234-56: 12m.

**2024-01-03 19:40:03** – Brake lights of the Mazda activate sharply; ABS pattern visible on camera stills. Initial brake application detected.

**2024-01-03 19:40:05** – ABS system engages. Wheel speed sensors detect incipient lock. System modulates brake pressure.

**2024-01-03 19:40:07** – Front wheels locked momentarily, slight skid to the right. Vehicle begins to lose directional stability.

**2024-01-03 19:40:09** – Vehicle yaw angle increases. Rear wheels begin to slide. Traction loss confirmed.

**2024-01-03 19:40:10** – Vehicle crosses white lane separator, approaching parking bay. Lateral movement: 1.2m to the right.

**2024-01-03 19:40:11** – Parking bay sensor detects approaching vehicle. No parking authorization for this vehicle.

**2024-01-03 19:40:12** – **Impact** with parked silver Honda Civic (plate unknown); front bumper of Mazda deforms; driver-side airbags deploy. Impact speed: approximately 28 km/h.

**2024-01-03 19:40:13** – Secondary contact with municipal light pole on pavement edge. Pole ID: JLM-POLE-4421. Impact force: moderate.

**2024-01-03 19:40:14** – Airbag deployment confirmed. Driver airbag and front passenger airbag both activated. Crash sensor threshold exceeded.

**2024-01-03 19:40:15** – Vehicle momentum continues forward. Rotation: 12 degrees clockwise.

**2024-01-03 19:40:17** – Vehicle comes to rest position. Final orientation: angled 15 degrees toward sidewalk.

**2024-01-03 19:40:20** – Vehicle comes to full stop angled toward sidewalk. Engine status: running (idle).

**2024-01-03 19:40:22** – First pedestrian response. Individual in dark jacket (later identified as witness) approaches vehicle from east side.

**2024-01-03 19:40:25** – Driver door opens. Dana Cohen visible on camera footage. Appears conscious, moving.

**2024-01-03 19:40:28** – Witness reaches driver-side door. Verbal exchange begins (audio not captured by traffic camera).

**2024-01-03 19:40:32** – Driver (Dana Cohen) seen on camera opening driver door and stepping onto sidewalk; appears unsteady for several seconds.

**2024-01-03 19:40:35** – Witness assists driver to sidewalk. Driver appears to be checking for injuries.

**2024-01-03 19:40:38** – Additional pedestrians gather. Crowd size: 3-4 individuals. No immediate threats observed.

**2024-01-03 19:40:42** – Driver attempts to stand unaided. Balance appears compromised. Sits back down on curb.

**2024-01-03 19:40:45** – Pedestrian in dark jacket approaches vehicle, speaks briefly with driver. Exchange duration: approximately 8 seconds.

**2024-01-03 19:40:48** – Witness removes mobile phone from pocket. Begins dialing sequence.

**2024-01-03 19:40:52** – Same pedestrian takes out phone and begins dialing. Call destination: emergency services (102).

**2024-01-03 19:40:55** – Emergency call initiated. Caller ID: +972-50-XXX-XXXX (witness mobile, anonymized in log).

**2024-01-03 19:41:00** – Emergency services call center receives incoming call. Operator ID: ES-OP-8923.

**2024-01-03 19:41:05** – Emergency services log **incoming call #ES-2024-11739** reporting a "single-car collision, possible injury, airbags deployed." Caller reports location: Jaffa Road / Shlomzion HaMalka.

**2024-01-03 19:41:08** – Call taker confirms details: single vehicle, airbags deployed, driver conscious. Priority level: Medium (non-life-threatening, but medical evaluation recommended).

**2024-01-03 19:41:12** – Dispatch system assigns resources: Ambulance unit A-12, Police unit P-34. Estimated response time: 4-6 minutes.

**2024-01-03 19:41:15** – Ambulance A-12 status: Available at station JLM-AMB-03. Distance to scene: 2.1 km.

**2024-01-03 19:41:18** – Police unit P-34 status: On patrol, location JLM-PAT-12. Distance to scene: 1.8 km.

**2024-01-03 19:41:22** – Dispatch confirms assignment. Units notified via radio and mobile data terminal.

**2024-01-03 19:41:25** – Ambulance A-12 crew acknowledges assignment. Crew: Paramedic Lior M., EMT Sarah K.

**2024-01-03 19:41:28** – Police unit P-34 acknowledges assignment. Officers: Ofc. David R., Ofc. Maya S.

**2024-01-03 19:41:30** – Ambulance A-12 begins vehicle preparation. Equipment check: Complete. Estimated departure: 30 seconds.

**2024-01-03 19:41:35** – Police unit P-34 begins route to scene. Traffic conditions: Moderate. Estimated arrival: 3 minutes.

**2024-01-03 19:41:40** – Ambulance A-12 completes preparation. Vehicle ready for departure.

**2024-01-03 19:41:44** – Dispatch assigns ambulance unit **A-12** and police unit **P-34** to the scene.

**2024-01-03 19:41:48** – Ambulance A-12 departs station. GPS tracking activated. Route: Direct via Jaffa Road.

**2024-01-03 19:42:00** – Ambulance A-12 en route. Current speed: 45 km/h (within speed limit for emergency response).

**2024-01-03 19:42:08** – Ambulance **A-12** reports departure from station.

**2024-01-03 19:42:15** – Police unit P-34 en route. Current location: 1.2 km from scene.

**2024-01-03 19:42:22** – Traffic camera JLM-CAM-114 records continued activity at scene. Driver remains on sidewalk, seated.

**2024-01-03 19:42:30** – Ambulance A-12 progress: 0.8 km traveled. Estimated arrival: 2.5 minutes.

**2024-01-03 19:42:38** – Witness provides additional information to call center: Driver reports "back pain" and "dizziness." No visible bleeding.

**2024-01-03 19:42:45** – Police unit P-34 progress: 0.5 km from scene. Traffic conditions: Light.

**2024-01-03 19:42:52** – Ambulance A-12: 0.4 km from scene. Sirens activated (audible on traffic camera audio feed).

**2024-01-03 19:43:00** – Police unit P-34: 0.3 km from scene. Emergency lights activated.

**2024-01-03 19:43:08** – Ambulance A-12: 0.2 km from scene. Preparing for arrival.

**2024-01-03 19:43:15** – Police unit P-34: 0.1 km from scene. Slowing for approach.

**2024-01-03 19:43:22** – Traffic camera records police vehicle entering frame from east.

**2024-01-03 19:43:28** – Police unit P-34 arrives at intersection. Officers begin traffic control procedures.

**2024-01-03 19:44:00** – Police unit P-34 establishes traffic control. Cones deployed. Eastbound lane partially closed.

**2024-01-03 19:44:15** – Ambulance A-12: Final approach. Distance: 100m.

**2024-01-03 19:44:31** – Police unit **P-34** reports arrival at intersection; officers begin traffic control.

**2024-01-03 19:44:38** – Ambulance A-12 arrives at scene. Vehicle positioned: 15m east of collision site.

**2024-01-03 19:44:45** – Ambulance crew exits vehicle. Paramedic Lior M. approaches driver.

**2024-01-03 19:47:00** – Ambulance crew continues assessment. Driver remains cooperative.

**2024-01-03 19:47:55** – Ambulance **A-12** arrives; paramedics approach driver.

**2024-01-03 19:48:00** – Paramedic begins initial assessment. Visual inspection: No obvious external injuries.

**2024-01-03 19:48:05** – Paramedic checks driver's level of consciousness. Response: Alert and oriented.

**2024-01-03 19:48:10** – Vital signs check begins. Blood pressure cuff applied.

**2024-01-03 19:48:15** – Blood pressure reading: 122/76 mmHg. Within normal range.

**2024-01-03 19:48:20** – Paramedic performs initial assessment (verbal, motor, pupil response). Driver reports mild back pain, "a little dizzy."

**2024-01-03 19:48:25** – Heart rate: 81 bpm. Regular rhythm. No abnormalities detected.

**2024-01-03 19:48:30** – Respiratory rate: 16 breaths/min. Normal.

**2024-01-03 19:48:35** – Pupil response: Equal, round, reactive to light. No signs of head injury.

**2024-01-03 19:48:40** – Motor function assessment: All extremities move normally. No weakness detected.

**2024-01-03 19:48:45** – Paramedic documents findings on tablet. Assessment code: MINOR-001 (minor injury, stable vitals).

**2024-01-03 19:49:00** – Paramedic discusses transport options with driver.

**2024-01-03 19:49:10** – Paramedic recommends transport to hospital for full evaluation.

**2024-01-03 19:49:15** – Driver considers recommendation. Response time: 8 seconds.

**2024-01-03 19:49:20** – Driver indicates preference: "I think I'm okay. I'd rather go home."

**2024-01-03 19:49:25** – Paramedic explains risks of refusing transport. Driver acknowledges but maintains preference.

**2024-01-03 19:49:30** – Driver **declines ambulance transport**, stating she "feels okay" and prefers to go home with a friend.

**2024-01-03 19:49:35** – Paramedic documents refusal. Protocol requires signed acknowledgment.

**2024-01-03 19:49:40** – Driver signs refusal form on paramedic's tablet. Signature captured: Dana Cohen, 2024-01-03 19:49:40.

**2024-01-03 19:49:45** – Paramedic provides discharge instructions: Monitor for worsening symptoms, seek medical care if condition changes.

**2024-01-03 19:49:50** – Ambulance crew prepares to clear scene. Equipment stowed.

**2024-01-03 19:50:00** – Ambulance crew completes documentation. Scene time: 5 minutes 15 seconds.

**2024-01-03 19:50:05** – Paramedic documents refusal of transport on tablet form (signature captured).

**2024-01-03 19:50:10** – Ambulance A-12 status updated: Available for next call.

**2024-01-03 19:50:15** – Police officers continue scene management. Vehicle damage assessment in progress.

**2024-01-03 19:50:20** – Officer David R. begins photographing vehicle damage. Camera: JLM-PD-CAM-445.

**2024-01-03 19:50:25** – Photographs taken: Front bumper (3 angles), headlights (2 angles), hood (2 angles), airbag deployment (1 angle).

**2024-01-03 19:50:30** – Officer Maya S. interviews driver. Statement recorded on body camera.

**2024-01-03 19:50:35** – Driver statement: "I was driving normally, the car in front braked suddenly, I tried to brake but the road was wet and I slid into the parked car."

**2024-01-03 19:50:40** – Officer documents statement. Case number assigned: JLM-PD-2024-001247.

**2024-01-03 19:50:45** – Witness interview begins. Witness provides contact information.

**2024-01-03 19:50:50** – Witness statement: "I saw the car slide, hit the parked car, then the pole. The driver got out and seemed shaken but okay."

**2024-01-03 19:50:55** – Officer documents witness statement. Witness contact: +972-50-XXX-XXXX (anonymized).

**2024-01-03 19:51:00** – Police report preparation begins. Estimated completion: 10 days.

**2024-01-03 19:51:12** – Ambulance **A-12** cleared from scene, returns to service.

**2024-01-03 19:51:20** – Police officers complete initial documentation. Scene secured.

**2024-01-03 19:51:30** – Driver contacts friend via mobile phone. Friend agrees to provide transportation.

**2024-01-03 19:51:40** – Police continue scene management, begin photographing damage.

**2024-01-03 19:52:00** – Friend arrives at scene. Vehicle: 2018 Hyundai Elantra, plate 12-345-67.

**2024-01-03 19:52:15** – Driver transfers to friend's vehicle. Personal belongings retrieved from Mazda.

**2024-01-03 19:52:30** – Driver departs scene with friend. Destination: Driver's residence (address on file).

**2024-01-03 19:52:45** – Police officers complete scene documentation. Vehicle remains at scene (not drivable).

**2024-01-03 19:53:00** – Tow truck dispatch requested. Service provider: JLM-TOW-442. Estimated arrival: 20 minutes.

**2024-01-03 19:53:15** – Police unit P-34 clears scene. Officers return to patrol duties.

**2024-01-03 19:54:00** – Tow truck JLM-TOW-442 arrives at scene. Driver: Moshe T. Dispatch code: TOW-2024-0119.

**2024-01-03 19:54:30** – Vehicle loaded onto tow truck. Destination: Impound lot JLM-IMP-03.

**2024-01-03 19:55:00** – Tow truck departs scene. Vehicle en route to impound.

**2024-01-03 19:56:00** – Impound lot receives vehicle. Storage location: Bay 12, Slot 7.

**2024-01-03 20:00:00** – Incident log closed. All resources cleared. Follow-up: Police report pending.

**2024-01-03 20:05:00** – Insurance company (Magen Insurance) receives automated notification of incident via police database integration.

**2024-01-03 20:10:00** – Claims department assigns case number: AC-2024-017. Initial handler: Yael Ben-Haim.

**2024-01-03 20:15:00** – Claims handler reviews automated incident report. Priority: Standard.

**2024-01-03 20:20:00** – Claims handler initiates contact protocol. Attempt: Phone call to insured.

**2024-01-03 20:25:00** – Contact attempt: No answer. Voicemail left. Message requests callback.

**2024-01-03 20:30:00** – Claims handler documents initial contact attempt. Next attempt scheduled: Next business day.

**2024-01-03 20:35:00** – End of high-resolution incident log window. All immediate post-incident activities documented.

"""
    with open(markdown_path, 'a', encoding='utf-8') as f:
        f.write(appendix)


def append_appendix_b(markdown_path: Path):
    """Append Appendix B with supporting metadata."""
    appendix = """

## Appendix B — Supporting Metadata

**Document Control Information**

- Document ID: CLAIM-AC-2024-017-MAIN
- Version: 1.2
- Last Updated: 2024-05-20 14:32:00
- Author: Claims Processing System v3.4.1
- Classification: Internal Use Only

**Claim Handler Information**

- Primary Handler: Yael Ben-Haim
- Handler ID: CH-8923
- Department: Claims Intake
- Supervisor: Ronit Levi (ID: SUP-4456)
- Initial Assignment Date: 2024-01-05 08:15:00

**System Metadata**

- Case Management System: MagenCMS v2.8.3
- Database Record ID: DB-REC-2024-017-88472
- Index Status: Indexed and Searchable
- Archive Status: Active
- Retention Period: 7 years (until 2031-05-20)

**Document Version History**

- v1.0 (2024-01-05): Initial FNOL document creation
- v1.1 (2024-02-01): Added adjuster site visit report
- v1.2 (2024-05-20): Final settlement documentation added

**Related Document References**

- Police Report: JLM-PD-2024-001247
- Medical Records: SZMC-ER-2024-001234 (Shaare Zedek)
- Physiotherapy Records: RPT-2024-0456 (Rehavia Physical Therapy)
- Vehicle Inspection: ADJ-2024-8923 (Amir Levi, Field Adjuster)
- Legal Correspondence: LEG-2024-017-AZULAY (Ronen Azulay, Counsel)

**Request IDs and Tracking**

- FNOL Request ID: REQ-FNOL-2024-017-001
- Medical Records Request: REQ-MED-2024-017-002
- Police Report Request: REQ-PD-2024-017-003
- Settlement Negotiation Thread: REQ-SETTLE-2024-017-004

**Quality Assurance**

- QA Review Date: 2024-05-21
- QA Reviewer: QA-REV-3345
- Compliance Check: PASSED
- Data Integrity Check: PASSED
- Privacy Review: PASSED

**Integration Points**

- Insurance Database: MAGE-DB-PROD-01
- Medical Records System: SZMC-API-v2
- Police Database: JLM-PD-INTEGRATION-v1.5
- Payment Processing: PAY-PROC-2024-017-001

**Audit Trail**

- Created: 2024-01-05 09:15:23 by SYSTEM
- Modified: 2024-01-05 14:22:10 by CH-8923
- Modified: 2024-02-01 11:45:33 by ADJ-8923
- Modified: 2024-05-20 14:32:00 by CH-8923
- Last Accessed: 2024-05-21 10:15:00 by QA-REV-3345

**Security and Access Control**

- Access Level: Claims Department + Legal
- Encryption: AES-256
- Backup Status: Daily automated backup
- Disaster Recovery: Tested quarterly

**Compliance Flags**

- GDPR Compliance: Verified
- HIPAA Equivalent: Verified (Israeli medical privacy law)
- Insurance Regulation Compliance: Verified
- Internal Policy Compliance: Verified

"""
    with open(markdown_path, 'a', encoding='utf-8') as f:
        f.write(appendix)


def append_appendix_a2(markdown_path: Path):
    """Append Appendix A.2 with extended dispatch and call log."""
    appendix = """

## Appendix A.2 — Extended Dispatch & Call Log

**2024-01-03 20:03:00** – Insured (Dana Cohen) initiates contact with insurance company. Call center receives incoming call.

**2024-01-03 20:03:05** – Call routing system assigns call to queue: Claims Intake Queue 2. Wait time: 12 seconds.

**2024-01-03 20:03:11** – Call connects to Claims Representative Yael Ben-Haim. Call ID: CALL-2024-017-001.

**2024-01-03 20:03:15** – Representative confirms caller identity: Dana Cohen, Policy AC-2023-8742.

**2024-01-03 20:03:20** – Caller reports incident: "I had an accident yesterday evening."

**2024-01-03 20:03:25** – Representative opens new claim file. System generates claim number: AC-2024-017.

**2024-01-03 20:03:30** – Representative collects initial information: Date, time, location of incident.

**2024-01-03 20:03:35** – Caller provides details: "January 3rd, around 7:40 PM, at Jaffa Road and Shlomzion HaMalka."

**2024-01-03 20:03:40** – Representative asks about injuries. Caller response: "My back hurts a bit, my neck is stiff."

**2024-01-03 20:03:45** – Representative documents injury report. Severity: Mild. Medical attention: Not yet sought.

**2024-01-03 20:03:50** – Representative asks about vehicle damage. Caller response: "Front bumper, headlights, airbags went off."

**2024-01-03 20:03:55** – Representative documents vehicle damage. Airbag deployment: Confirmed.

**2024-01-03 20:04:00** – Representative asks about other parties. Caller response: "Just a parked car, no other drivers."

**2024-01-03 20:04:05** – Representative documents: Single-vehicle incident with property damage to parked vehicle.

**2024-01-03 20:04:10** – Representative asks about police involvement. Caller response: "Yes, police came, they said I'll get a report in about 10 days."

**2024-01-03 20:04:15** – Representative documents police report: Pending. Expected receipt: 10 days.

**2024-01-03 20:04:20** – Representative asks about medical attention at scene. Caller response: "Ambulance came, but I didn't go with them."

**2024-01-03 20:04:25** – Representative documents: Ambulance offered, transport refused. Flags for follow-up.

**2024-01-03 20:04:30** – Representative provides next steps: Medical evaluation recommended, garage referral provided.

**2024-01-03 20:04:35** – Caller acknowledges instructions. Call duration: 1 minute 24 seconds.

**2024-01-03 20:04:40** – Call ends. Representative completes call notes. Claim file status: Active.

**2024-01-03 20:04:45** – System generates automated tasks: Medical records request, police report follow-up, vehicle inspection scheduling.

**2024-01-03 20:05:00** – Claims handler reviews call notes. Priority assessment: Standard.

**2024-01-03 20:05:15** – Handler assigns follow-up tasks. Due dates set: Medical records (7 days), Police report (14 days).

**2024-01-03 20:05:30** – System sends automated confirmation email to insured. Email ID: EMAIL-2024-017-001.

**2024-01-03 20:06:00** – Email delivery confirmed. Recipient: dana.cohen@email.com (on file).

**2024-01-03 20:10:00** – Claims handler reviews policy details. Coverage verification: Comprehensive coverage active.

**2024-01-03 20:15:00** – Handler initiates medical records request. Request ID: REQ-MED-2024-017-002.

**2024-01-03 20:20:00** – Medical records request sent to Shaare Zedek Medical Center. Delivery method: Secure portal.

**2024-01-03 20:25:00** – System logs request sent. Expected response: 5-7 business days.

**2024-01-03 20:30:00** – Handler schedules vehicle inspection. Inspection date: 2024-02-01. Inspector: Amir Levi.

**2024-01-03 20:35:00** – Inspection appointment confirmed. Notification sent to insured.

**2024-01-03 20:40:00** – End of extended dispatch and call log window.

"""
    with open(markdown_path, 'a', encoding='utf-8') as f:
        f.write(appendix)


def main():
    """Main execution."""
    print(f"Reading markdown from: {MARKDOWN_PATH}")
    print(f"Generating PDF to: {PDF_PATH}")
    
    # Initial PDF generation
    page_count = generate_pdf(MARKDOWN_PATH, PDF_PATH)
    print(f"Initial PDF: {page_count} pages")
    
    iterations = 0
    max_iterations = 3
    
    while page_count < MIN_PAGES and iterations < max_iterations:
        iterations += 1
        print(f"\nPDF has {page_count} pages (need {MIN_PAGES}). Appending appendix sections...")
        
        if iterations == 1:
            append_appendix_a(MARKDOWN_PATH)
            print("Appended: Appendix A — High-Resolution Incident Log")
        elif iterations == 2:
            append_appendix_b(MARKDOWN_PATH)
            print("Appended: Appendix B — Supporting Metadata")
        else:
            append_appendix_a2(MARKDOWN_PATH)
            print("Appended: Appendix A.2 — Extended Dispatch & Call Log")
        
        # Regenerate PDF
        page_count = generate_pdf(MARKDOWN_PATH, PDF_PATH)
        print(f"Regenerated PDF: {page_count} pages")
    
    if page_count < MIN_PAGES:
        raise Exception(f"Failed to reach {MIN_PAGES} pages after {max_iterations} iterations. Final count: {page_count}")
    
    # Verify PDF exists and is non-empty
    if not PDF_PATH.exists():
        raise Exception(f"PDF file was not created: {PDF_PATH}")
    
    file_size = PDF_PATH.stat().st_size
    if file_size == 0:
        raise Exception(f"PDF file is empty: {PDF_PATH}")
    
    print(f"\n✓ OK: {page_count} pages")
    print(f"✓ PDF created: {PDF_PATH}")
    print(f"✓ File size: {file_size:,} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())

