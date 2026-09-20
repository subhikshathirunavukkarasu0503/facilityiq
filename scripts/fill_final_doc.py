from __future__ import annotations
from pathlib import Path
from copy import deepcopy
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_BREAK, WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT

ROOT=Path(__file__).resolve().parents[1]
TEMPLATE=Path('/downloads/file-d97a193c.docx')
OUT=ROOT/'docs/S4-I-18_Subhiksha_Thirunavukkarasu_FinalTermDoc.docx'
REPO='https://github.com/subhikshathirunavukkarasu0503/facilityiq'
COMMIT='ae4a8b4df6493998431db7f1c29786b9c15fd6fa'
MID='S4-I-18_Subhiksha_Thirunavukkarasu_MidTermDoc.docx'
EVID=ROOT/'docs/evidence/final'

def setc(c,s):
 c.text=str(s)
 for p in c.paragraphs:
  for r in p.runs: r.font.size=Pt(8.5)
  p.paragraph_format.space_after=Pt(2)
 c.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER

def fillrow(t,r,vals,start=0):
 while r>=len(t.rows): t.add_row()
 for i,v in enumerate(vals): setc(t.rows[r].cells[start+i],v)

def replace_after_heading(doc,heading,text):
 for i,p in enumerate(doc.paragraphs):
  if p.text.strip()==heading:
   target=doc.paragraphs[i+1]
   target.text=text
   target.style=doc.styles['Normal']
   return
 raise KeyError(heading)

def add_picture_after_table(table,path,width=Inches(6.5)):
 para=table._parent.add_paragraph()
 table._tbl.addnext(para._p)
 para.alignment=WD_ALIGN_PARAGRAPH.CENTER
 para.add_run().add_picture(str(path),width=width)

def main():
 d=Document(str(TEMPLATE)); T=d.tables
 # Remove template instruction paragraphs but retain all numbered section headings.
 remove=[]
 for p in d.paragraphs:
  s=p.text.strip()
  if (s.startswith('READ BEFORE') or s.startswith('•  ') or s.startswith('• ')
      or s.startswith('Copy these fields') or s.startswith('Summarise directly')
      or s.startswith('Describe the architecture') or s.startswith('List only tools')
      or s.startswith('The core of your submission') or s.startswith('Compare against')
      or s.startswith('One consolidated evidence') or s.startswith('One row per evidence')
      or s.startswith('These links are checked') or s.startswith('Report all QA')
      or s.startswith('List every tool') or s.startswith('List ANY change')
      or s.startswith('Anything you built') or s.startswith('Be specific and honest')
      or s.startswith('Carry forward every risk') or s.startswith('Tick every box')
      or s.startswith('Need more blocks?') or s.startswith('[ Paste screenshot')):
   remove.append(p)
 for p in remove: p._element.getparent().remove(p._element)

 # Section 1
 vals=['S4-I-18','Smart Facility Management Platform','Subhiksha Thirunavukkarasu','P399',
       '☑ Custom      ☐ Data      ☐ Platform',
       'Semester 4 — Integration Mastery (Capstone): E2E Integration with IoT, ML/AI Core, Azure Deployment, QA Mandatory',
       '☑ Regular      ☐ pSiddhi Lite','₹2,500 (fixed)',MID,
       '☐ On track   ☐ At risk — actions were assigned   ☑ Other: official result/feedback not supplied',
       'Week 17 — submission due 21-Sep-2026; exact review dates not supplied']
 for i,v in enumerate(vals): fillrow(T[0],i,[v],1)

 replace_after_heading(d,'2.1 Problem Statement (as approved)',
  'No change from Mid-Term recap. Facility teams operate reactively because available HVAC, electrical and occupancy telemetry is not converted into decisions. FacilityIQ addresses preventable failures, invisible space use, energy waste and calendar-based maintenance through integrated telemetry, ML scoring and an operational portal.')
 replace_after_heading(d,'2.2 Proposed Solution Summary (as approved)',
  'FacilityIQ implements simulated three-domain devices, unified validation, a JSONL data lake mirrored to Azure Blob, feature pipelines, three scikit-learn models and a five-screen Streamlit portal. The direct-to-Blob path remains the working Azure fallback because corporate RBAC blocked IoT Hub, Functions and App Service provisioning. Final QA adds Great Expectations, Selenium browser journeys and Locust load testing. Three report-ready datasets were validated and used to create live Power BI Service reports for equipment health, energy consumption and space utilization.')
 replace_after_heading(d,'2.3 Core Tools & AI Components (as approved)',
  'Azure IoT Hub, Azure Functions, Azure Blob Storage, Azure App Service; Databricks Community and MLflow; scikit-learn and PyCaret; Streamlit; Power BI Desktop; Gemini; Ollama/Llama; GitHub Actions; Pytest, Selenium and Great Expectations. Actual usage and substitutions are reconciled in Section 7. The supplied project record also includes Groq, but the official L&D feedback that allegedly required it was not supplied for independent verification.')

 # Section 3
 rows=[
 ('D-01','Azure setup, telemetry schema and HVAC simulators','Week 4','Y','Partial','EV-04, EV-06 (Mid-Term)'),
 ('D-02','Energy/space simulators and 3-domain landing zone','Week 5','Y','Done','EV-04, EV-06 (Mid-Term), EV-07'),
 ('D-03','Lake-to-analytics feature pipeline','Week 6','Y','Done','EV-04, EV-05 (Mid-Term), EV-07'),
 ('D-04','HVAC Random Forest trained and measured','Week 7','Y','Done','EV-04 (Mid-Term), EV-09'),
 ('D-05','Electrical Isolation Forest and motor GBM','Week 8','Y','Done','EV-04 (Mid-Term), EV-09'),
 ('D-06','Portal health overview and equipment detail','Week 9','Y','Done','EV-01–EV-03 (Mid-Term)'),
 ('D-07','Embedded unit/integration/model/UI QA and CI','Weeks 4–9','Y','Done','EV-05 (Mid-Term), EV-08'),
 ('D-08','Role-based login, maintenance and AI screens','Weeks 11–12','Y','Done','EV-01, EV-03 (Mid-Term)'),
 ('D-09','Power BI dashboards: equipment, energy and space','Week 13','N','Done','EV-11'),
 ('D-10','Scale and browser E2E validation','Week 14','N','Done','EV-08'),
 ('D-11','Great Expectations data quality and full regression','Week 15','N','Done','EV-07, EV-08'),
 ('D-12','Final documentation, evidence and review preparation','Week 16','N','Done','EV-07–EV-11'),
 ]
 for i,r in enumerate(rows,1): fillrow(T[1],i,list(r))
 fillrow(T[2],0,['Complete three-domain ingestion, three prediction scenarios, four portal screens, three analytics dashboards, Azure deployment, at least 10,000 telemetry points and a QA suite with at least 80% measured coverage.'],1)
 fillrow(T[2],1,['88% — core telemetry, models, portal, AI, QA and three Power BI Service reports are working and evidenced. The corporate-access-blocked IoT Hub/Functions/App Service route prevents a 100% claim.'],1)
 fillrow(T[2],2,['90% of the Week-10 checkpoint (not 90% of the full programme).'],1)
 fillrow(T[2],3,['☐ Yes, end-to-end      ☑ Yes, partially      ☐ No, recording/screenshots only'],1)

 # Evidence index, add two rows for EV-11/12 and continue numbering.
 evidence=[
 ('EV-01','Role-based login and admin panel','D-06, D-08',REPO,'Yes — Mid-Term EV-01'),
 ('EV-02','Health overview, ranked alerts and live context','D-05, D-06',REPO,'Yes — Mid-Term EV-02'),
 ('EV-03','Equipment, maintenance and AI portal screens','D-06, D-08',REPO,'Yes — Mid-Term EV-03'),
 ('EV-04','Three held-out ML model result sets and lake scale','D-01–D-05',REPO+'/tree/main/models','Yes — Mid-Term EV-04'),
 ('EV-05','Measured Mid-Term coverage and green CI','D-03, D-07',REPO+'/actions','Yes — Mid-Term EV-05'),
 ('EV-06','Azure Blob lake and repository history','D-01, D-02',REPO+'/commits/main','Yes — Mid-Term EV-06'),
 ('EV-07','Great Expectations: 14,784 records, 51/51 checks, 0 duplicates','D-02, D-03, D-11',REPO+'/tree/'+COMMIT+'/docs/evidence/final','No — new'),
 ('EV-08','80-test regression, 87% coverage, Selenium 2/2, Locust 1,402 requests/0 failures','D-07, D-10, D-11',REPO+'/tree/'+COMMIT+'/docs/evidence/final','No — new'),
 ('EV-09','Final model metrics and honest completion boundary','D-04, D-05, D-12',REPO+'/tree/'+COMMIT+'/docs/evidence/final','No — new'),
 ('EV-10','Final source/evidence commit and Power BI datasets','D-09–D-12',REPO+'/commit/'+COMMIT,'No — new'),
 ('EV-11','Three live Power BI Service reports and semantic models','D-09',REPO+'/tree/'+COMMIT+'/docs/evidence/final','No — new'),
 ]
 for i,r in enumerate(evidence,1): fillrow(T[3],i,list(r))

 # Six supplied blocks become EV-07..EV-12. Only first three carry images.
 blocks=[
 ('EV-07 — Final telemetry data-quality gate','Great Expectations validated every committed lake record: 195 files, 14,784 records, 0 duplicate device/timestamp pairs and 51/51 domain expectations passed.','D-02, D-03, D-11','20-Sep-2026',REPO+'/tree/'+COMMIT+'/docs/evidence/final','☑ No (new / progressed)',EVID/'ev07_data_quality.png'),
 ('EV-08 — Final regression, browser E2E and load run','80 pytest tests passed with 87% statement coverage; 2/2 Selenium journeys passed; Locust produced 1,402 requests with 25 concurrent users, 0 failures and p99 5 ms on the local Streamlit HTTP surface.','D-07, D-10, D-11','20-Sep-2026',REPO+'/tree/'+COMMIT+'/docs/evidence/final','☑ No (new / progressed)',EVID/'ev08_qa_load.png'),
 ('EV-09 — Model results and completion boundary','Confirms current held-out model metrics and explicitly separates delivered scope from cloud components blocked during the final Azure validation attempt.','D-04, D-05, D-12','20-Sep-2026',REPO+'/tree/'+COMMIT+'/docs/evidence/final','☑ No (new / progressed)',EVID/'ev09_models_scope.png'),
 ('EV-10 — Final source, evidence and dataset commits','Commits 3bac9f2 through ae4a8b4 add the Great Expectations validator, Locust profile, Selenium journeys, tests, raw result files and three validated Power BI datasets.','D-10–D-12','20-Sep-2026',REPO+'/commit/'+COMMIT,'☑ No (new / progressed)',None),
 ('EV-11 — Three Power BI Service reports','Live reports and semantic models were created in My workspace for Equipment Health, Energy Consumption and Space Utilization. Each report contains a real table visual built from the validated CSV export.','D-09','21-Sep-2026','Equipment: https://app.powerbi.com/groups/me/reports/ced34aee-008a-46a2-b0fa-ffb1a9b85d80?experience=power-bi ; Energy: https://app.powerbi.com/groups/me/reports/e09268d2-7f5d-4518-bab2-1fd9f39734f2?experience=power-bi ; Space: https://app.powerbi.com/groups/me/reports/388c3a7f-1caf-469b-a779-da2b1d136041?experience=power-bi','☑ No (new / progressed)',EVID/'ev11_powerbi_reports.png'),
 ('EV-12 — Not used','No additional evidence claimed.','N/A','N/A','N/A','☑ No (not used)',None),
 ]
 block_heads=[p for p in d.paragraphs if p.text.startswith('EV-') and 'replace with' in p.text]
 for p,b in zip(block_heads,blocks): p.text=b[0]
 for i,b in enumerate(blocks):
  for r,v in enumerate(b[1:6]): fillrow(T[4+i],r,[v],1)
  if b[6]: add_picture_after_table(T[4+i],b[6])

 # Section 5
 fillrow(T[10],0,[REPO],1); fillrow(T[10],1,[COMMIT+' — 20-Sep-2026'],1)
 fillrow(T[10],2,['https://facilityiq-subhiksha.streamlit.app — currently redirects to Streamlit authentication; local portal remains the demonstrable fallback'],1)
 fillrow(T[10],3,[REPO+'/tree/'+COMMIT+'/docs/evidence/final'],1)
 walk=[
 ('Great Expectations telemetry quality gate','src/facilityiq/qa/data_quality.py; scripts/run_data_quality.py; tests/test_data_quality.py'),
 ('Browser and load QA','tests/test_selenium_e2e.py; locustfile.py; docs/evidence/final/'),
 ('Branch','main at commit '+COMMIT),
 ('Open in advance','data/lake; models/*_metrics.json; docs/evidence/final/data_quality_report.json; locust_report.html')]
 for i,(a,b) in enumerate(walk): fillrow(T[11],i,[a,b])

 qa=[
 ('Unit + integration + model + UI regression','80 passed; 3 environment-gated skips','87% measured statement coverage','>80%','EV-08'),
 ('Great Expectations data quality','14,784 records; 51/51 expectations passed','100% expectation pass; 0 duplicates','Zero invalid records','EV-07'),
 ('Selenium browser E2E','2 journeys: admin five-screen navigation and viewer restriction','2/2 passed','5 E2E scenarios proposed; 2 final browser journeys executed','EV-08'),
 ('Locust load test','25 users, 30 sec, 1,402 requests','0 failures; p99 5 ms; 47.13 req/s','<2 sec portal response','EV-08')]
 for i,r in enumerate(qa,1): fillrow(T[12],i,list(r))

 tools=[
 ('Azure IoT Hub','F1 Free / ₹0','No','0','Draft validated to final review, then Azure returned a generic Validation failed; no resource was created.'),
 ('Azure Functions','Free / ₹0','No','0','Depends on IoT Hub provisioning; not claimed.'),
 ('Azure Blob Storage','Free/low-cost','Yes','Not independently verified after Mid-Term','Direct lake fallback documented at Mid-Term.'),
 ('Azure App Service','Free / ₹0','No','0','Plan creation blocked by corporate RBAC; Streamlit fallback.'),
 ('Databricks + MLflow','Free','Partial','0','Local pandas/scikit-learn; MLflow retained locally.'),
 ('scikit-learn + PyCaret','Free','Partial','0','scikit-learn used; PyCaret omitted.'),
 ('Power BI Service','Free / existing organisational licence','Yes','0','Three reports and three semantic models created in My workspace from validated CSV exports.'),
 ('Streamlit','Free','Yes','0','Five-screen portal and local QA target.'),
 ('Gemini','Free tier / ₹400 provision','Yes','0 reported','Narratives use cache/fallback.'),
 ('Ollama + Llama','Free','No','0','Not needed; retained only as planned fallback.'),
 ('GitHub + Actions','Free','Yes','0','Repository, history and CI workflow.'),
 ('Pytest + Selenium','Free','Yes','0','80 passing tests; 2 final browser journeys.'),
 ('Great Expectations','Free','Yes','0','51/51 final data expectations passed.'),
 ('Domain (optional)','₹450','No','0','Optional purchase omitted.'),
 ('Groq API','Free tier','Yes, per supplied project record','0','Included in source; claimed L&D condition remains unverified without official feedback.')]
 for i,r in enumerate(tools,1): fillrow(T[13],i,list(r))
 budgets=[('Approved budget ceiling','₹2,500'),('Actual spend till Mid-Term','₹0 reported in Mid-Term'),('Actual spend, Mid-Term to Final','₹0 reported; Azure storage billing not independently accessible'),('Total actual spend','₹0 reported, subject to owner account verification'),('Buffer remaining','₹2,500 reported, subject to owner account verification')]
 for i,r in enumerate(budgets): fillrow(T[14],i,list(r))

 dev=[
 ('IoT ingestion path','IoT Hub → Functions → Blob','Validated local lake → direct Azure Blob fallback; IoT client code retained','Carried from Mid-Term; corporate RBAC blocked provisioning.'),
 ('ML compute','Databricks + PyCaret','Local pandas/scikit-learn; local MLflow','Carried from Mid-Term; appropriate for POC volume.'),
 ('Deployment','Azure App Service','Streamlit local/cloud fallback; cloud URL currently auth-gated','Carried from Mid-Term; App Service plan blocked.'),
 ('Analytics dashboards','Power BI x3','Three live Power BI Service reports backed by validated CSV exports','Completed on 21-Sep-2026; live URLs and screenshots recorded in EV-11.'),
 ('QA completion','Great Expectations, load and E2E planned','Implemented and executed in final phase','New final-phase completion on 20-Sep-2026.')]
 for i,r in enumerate(dev,1): fillrow(T[15],i,list(r))
 enh=[
 ('EN-01','Four-role access control and admin view','Controls screen access and supports operational demos','Done','0','Mid-Term EV-01'),
 ('EN-02','Live weather, air quality and footfall context','Adds external operational context','Done','0','Mid-Term EV-02/03'),
 ('EN-03','Dual AI provider and deterministic cache/template fallback','Keeps explanations available during API/network failure','Done','0','Mid-Term EV-03'),
 ('EN-04','Automated final data-quality and load evidence','Turns final QA into repeatable scripts and machine-readable reports','Done','0','EV-07, EV-08')]
 for i,r in enumerate(enh,1): fillrow(T[16],i,list(r))
 pending=[
 ('IoT Hub + Functions live route','Corporate Azure RBAC prevented resource creation','Y','Provision in the assigned RG, set the device connection string, verify route to existing Blob container.'),
 ('Azure App Service deployment','Corporate RBAC prevented plan creation','Y','Deploy after IT provisions F1 plan; retain Streamlit as backup.'),
 ('Public cloud portal access','Current Streamlit URL redirects to Streamlit authentication','N','Change sharing settings or grant reviewer access before review.'),
 ('Official Mid-Term result/feedback and final review dates','Not supplied with project materials','N','Attach official feedback and update Section 1 before submission if available.')]
 for i,r in enumerate(pending,1): fillrow(T[17],i,list(r))
 risks=[
 ('Azure subscription validation blocks IoT Hub/App Service','Accepted','Direct-Blob and local/Streamlit fallbacks retained; the final IoT Hub attempt returned a generic validation failure and created no resource.','Core POC works; approved cloud route is incomplete.'),
 ('Model accuracy below target','Mitigated','Grouped held-out testing; final metrics retained in repository.','HVAC and motor exceed F1 target; electrical recall is 1.00.'),
 ('AI/API availability','Mitigated','Caching, provider fallback and deterministic templates.','Portal remains usable without live narrative call.'),
 ('Power BI report depth','Mitigated','Created three live reports with table visuals and retained validated source datasets.','Reports exist and are evidenced; further visual design remains optional refinement.'),
 ('Credential exposure in supplied spreadsheet','Realised','Key rotation and password rotation requested; secrets omitted from this document.','Owner must rotate exposed key/passwords before review.')]
 for i,r in enumerate(risks,1): fillrow(T[18],i,list(r))
 fillrow(T[19],0,['Subhiksha Thirunavukkarasu'],1); fillrow(T[19],1,['21-Sep-2026'],1)

 # Check only statements established by this doc; leave user-dependent checks open.
 for p in d.paragraphs:
  if p.text.startswith('☐  Section 3') or p.text.startswith('☐  Deliverables') or p.text.startswith('☐  Every "Done"') or p.text.startswith('☐  Every evidence') or p.text.startswith('☐  Section 6') or p.text.startswith('☐  Section 7') or p.text.startswith('☐  Section 8') or p.text.startswith('☐  Section 9') or p.text.startswith('☐  Section 10') or p.text.startswith('☐  I have deleted') or p.text.startswith('☐  I have not renamed') or p.text.startswith('☐  Document is saved'):
   p.text='☑'+p.text[1:]

 # Conservative page layout and fonts.
 for sec in d.sections:
  sec.top_margin=Inches(.45); sec.bottom_margin=Inches(.35); sec.left_margin=Inches(.55); sec.right_margin=Inches(.55)
 d.styles['Normal'].font.name='Aptos'; d.styles['Normal'].font.size=Pt(9)
 for p in d.paragraphs:
  p.paragraph_format.space_after=Pt(4)
 d.save(str(OUT)); print(OUT)
if __name__=='__main__': main()
