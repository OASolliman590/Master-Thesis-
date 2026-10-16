from pathlib import Path
import json, re, hashlib, tempfile, os
from xml.sax.saxutils import escape
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle, Flowable, KeepTogether
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import A4

ROOT = Path(__file__).resolve().parent
OUT = ROOT/'Thesis_Papers_SpecKit_and_Epigenetic_Priming_Guide_Amendment_20261016.pdf'
TMP = Path(tempfile.mkdtemp(prefix='thesis-guide-'))
SNAPSHOT = '92f9099c1a2e5442590729cce6d54f1a81958f27'
BASE = f'https://github.com/OASolliman590/Master-Thesis-/blob/{SNAPSHOT}/'
FONT = Path(os.environ.get('THESIS_FONT_DIR', '/System/Library/Fonts/Supplemental'))
for name, file in [('Body','Arial.ttf'),('BodyBold','Arial Bold.ttf'),('BodyItalic','Arial Italic.ttf'),('Display','Georgia.ttf')]:
    pdfmetrics.registerFont(TTFont(name,str(FONT/file)))
pdfmetrics.registerFontFamily('Body',normal='Body',bold='BodyBold',italic='BodyItalic',boldItalic='BodyBold')
NAVY=colors.HexColor('#183449'); TEAL=colors.HexColor('#007D83'); INK=colors.HexColor('#273846'); MUTED=colors.HexColor('#5A6D79'); LIGHT=colors.HexColor('#EDF4F5'); GOLD=colors.HexColor('#AE722E')
W,H=A4; CW=W-92
styles={
 'body':ParagraphStyle('body',fontName='Body',fontSize=10.5,leading=14.5,textColor=INK,spaceAfter=7),
 'small':ParagraphStyle('small',fontName='Body',fontSize=8.3,leading=11.3,textColor=MUTED,spaceAfter=5),
 'title':ParagraphStyle('title',fontName='Display',fontSize=25,leading=30,textColor=NAVY,spaceAfter=14),
 'sub':ParagraphStyle('sub',fontName='BodyBold',fontSize=12,leading=16,textColor=TEAL,spaceBefore=10,spaceAfter=5),
 'kicker':ParagraphStyle('kicker',fontName='BodyBold',fontSize=8.8,leading=12,textColor=TEAL,spaceAfter=9),
 'cell':ParagraphStyle('cell',fontName='Body',fontSize=9.1,leading=12.4,textColor=INK),
 'cellhead':ParagraphStyle('cellhead',fontName='BodyBold',fontSize=9.1,leading=12.4,textColor=colors.white),
 'callout':ParagraphStyle('callout',fontName='Body',fontSize=10.6,leading=15,textColor=NAVY),
}
story=[]; page_titles=[]; content=[]
def p(text,style='body'):
    story.append(Paragraph(text,styles[style]));content.append(re.sub('<[^>]+>','',text))
def section(kicker,title):
    if page_titles:story.append(PageBreak())
    page_titles.append(title);p(kicker.upper(),'kicker');p(title,'title')
def h(text):p(text,'sub')
def callout(text):
    t=Table([[Paragraph(text,styles['callout'])]],colWidths=[CW]);t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),LIGHT),('BOX',(0,0),(-1,-1),.6,colors.HexColor('#C8DEDF')),('LEFTPADDING',(0,0),(-1,-1),12),('RIGHTPADDING',(0,0),(-1,-1),12),('TOPPADDING',(0,0),(-1,-1),10),('BOTTOMPADDING',(0,0),(-1,-1),10)]));story.append(t);story.append(Spacer(1,9));content.append(re.sub('<[^>]+>','',text))
def table(headers,rows,widths):
    data=[[Paragraph(x,styles['cellhead']) for x in headers]]+[[Paragraph(x,styles['cell']) for x in r] for r in rows]
    t=Table(data,colWidths=[CW*x for x in widths],repeatRows=1,hAlign='LEFT')
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),NAVY),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,LIGHT]),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),8),('RIGHTPADDING',(0,0),(-1,-1),8),('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),8),('LINEBELOW',(0,0),(-1,0),.5,NAVY)]));story.append(t);story.append(Spacer(1,9));content.extend([' | '.join(r) for r in rows])
def source(ids):p('Source basis: '+ids+'. Canonical source links and version details are on pages 20-21.','small')

class Ecosystem(Flowable):
    def __init__(self): Flowable.__init__(self);self.width=CW;self.height=265
    def draw(self):
        c=self.canv
        def box(x,y,w,h,title,desc,fill=LIGHT):
            c.setFillColor(fill);c.setStrokeColor(colors.HexColor('#B6CCD0'));c.roundRect(x,y,w,h,7,fill=1,stroke=1)
            c.setFillColor(NAVY);c.setFont('BodyBold',10);c.drawString(x+10,y+h-18,title)
            txt=Paragraph(desc,styles['small']);_,ht=txt.wrap(w-20,h-25);txt.drawOn(c,x+10,y+h-28-ht)
        def arrow(x1,y1,x2,y2,dashed=False):
            c.setStrokeColor(TEAL);c.setFillColor(TEAL);c.setLineWidth(1.2)
            if dashed:c.setDash(3,3)
            c.line(x1,y1,x2,y2);c.setDash()
            import math
            ang=math.atan2(y2-y1,x2-x1);q=c.beginPath();q.moveTo(x2,y2)
            q.lineTo(x2-6*math.cos(ang-.5),y2-6*math.sin(ang-.5));q.lineTo(x2-6*math.cos(ang+.5),y2-6*math.sin(ang+.5));q.close();c.drawPath(q,fill=1,stroke=0)
        bw=(CW-30)/3
        box(0,182,bw,70,'A  Clinical reference','Baseline association and independent prediction')
        box(bw+15,182,bw,70,'B  Prostate context','Immune deficits and epigenetic evidence')
        box(2*(bw+15),182,bw,70,'C  Perturbation','Measured responsiveness and prioritisation')
        arrow(bw,217,bw+15,217);arrow(2*bw+15,217,2*bw+30,217)
        box(0,87,bw,65,'A.1  Time course','Paired, response-associated change')
        box(bw+15,87,bw,65,'D  Predictive models','Molecular benchmark; tumour-T-cell model')
        box(2*(bw+15),87,bw,65,'E  Exposure & timing','Public-data PK/PD, QSP and uncertainty')
        arrow(bw/2,182,bw/2,152,True);arrow(2*bw+30+bw/2,182,bw+15+bw/2,152,True)
        arrow(2*bw+15,119,2*bw+30,119,True)
        box(bw+15,0,2*bw+15,57,'E_LAST  Optional measured extension','Accepted E foundation + admitted original observations')
        arrow(2*bw+30+bw/2,87,2*bw+30+bw/2,57)
        c.setFillColor(MUTED);c.setFont('Body',8);c.drawString(0,46,'Solid: defined evidence handoff')
        c.drawString(0,32,'Dashed: contextual / gated link')
        c.drawString(0,18,'Arrows do not prove causation.')

section('MSc thesis | Reader guide | 16 October 2026','Epigenetic priming\n<br/>in prostate cancer')
p('The papers, the specification kit, and the scientific ecosystem','sub')
p('A guide to the scope, aims and intended outputs of Papers A, A.1, B, C, D and E, with the optional E_LAST extension. It explains both the software structure of the SpecKit and the scientific reasoning encoded in that structure.')
callout('<b>Central thesis question</b><br/>Which immune-related states are clinically relevant, which are associated with epigenetic regulation in prostate cancer, which can respond to perturbation, and under what evidence-supported conditions could priming improve immune recognition or function?')
p('This revised companion explains RC2 plus the separately versioned, user-authorized A/A.1 immune-programme amendment and Paper B alignment. The amendment is detailed on pages 22-26. It reports no new biological results and authorizes no biological execution. Throughout, <b>output</b> means an intended deliverable unless explicitly identified as existing software or verification evidence.')
h('How to read this guide')
table(['Part','What it explains','Pages'],[
 ['The scientific ecosystem','Why the programme is connected, and why the evidence must remain distinguishable.','2-3'],
 ['The papers','Aim, scope, method, outputs and limits for each paper or extension.','4-10'],
 ['The SpecKit','Shared data foundations, technical structure, component meanings and interfaces.','11-15'],
 ['Interpretation and readiness','A worked example, release gates, synthesis and glossary.','16-19'],
 ['Sources','Immutable RC2 source map and selected primary scientific references.','20-21'],
],[.22,.64,.14])
p('<b>Version basis:</b> specs/thesis-20261015-v1-rc2, snapshot 92f9099c1a2e5442590729cce6d54f1a81958f27. The 696 scoped source files were hash-checked before authoring. RC1 was superseded for packaging; RC2 is still a review-branch specification candidate.','small')

section('01 | Programme architecture','One question, several kinds of evidence')
p('The programme connects clinical observations, prostate molecular evidence, perturbation experiments, predictive models and pharmacological constraints. Each paper answers a different question. Agreement between them can strengthen a hypothesis, but repeating the same source data in multiple papers does not create independent evidence.')
story.append(Ecosystem());story.append(Spacer(1,10))
table(['Module','Its contribution to the common question'],[
 ['A / A.1','What immune programmes are associated with ICI response, before treatment and during treatment?'],
 ['B','Which relevant programmes are deficient in prostate contexts, and what epigenetic evidence accompanies those deficits?'],
 ['C','Does epigenetic support improve the choice of molecular targets for perturbation, and which interventions deserve further testing?'],
 ['D','Can specified models predict measured molecular or tumour-T-cell behaviour beyond explicit baselines?'],
 ['E / E_LAST','What does public evidence support about exposure and timing, and what can new measurements add?'],
],[.18,.82])
p('<b>Dependency nuance:</b> B-P can proceed independently of A when its own gates close. A.1 need not await B/C. Measured-driver D2 does not require a successful D1 model. E core requires neither D nor original experiments; only E_LAST depends on an accepted E foundation. The diagram is an evidence map, not a mandatory execution sequence.')
source('S1, S2, S9, S12-S15')

section('02 | Scientific rationale','What does epigenetic priming mean here?')
p('In this thesis, <b>priming</b> is a research hypothesis: changing an epigenetically regulated state may make a tumour-immune system more capable of responding to an immune intervention. The programme separates a molecular change from a functional effect and from a clinical benefit. Those are different outcomes, requiring different measurements.')
h('Why the hypothesis is worth testing')
p('In selected experimental systems, DNA-methylation inhibition induced endogenous-retrovirus-associated double-stranded RNA and an interferon response. Preclinical sensitisation to checkpoint blockade provides a rationale for studying epigenetic-immune interactions, but does not establish the same mechanism or benefit in prostate cancer. [R1]')
p('Prostate-specific evidence also complicates the simple idea that "less methylation means more immune-gene expression". Guo and colleagues linked hypomethylated chromatin domains to repression of immune-related genes in prostate cancer. Local promoter methylation, larger domains and cellular context therefore need distinct interpretations. [R2]')
p('The KEYNOTE-199 study reported limited objective response in its studied, previously treated metastatic castration-resistant prostate cancer cohorts, while some responses were durable. This motivates a context-specific investigation of immune barriers; it does not show that epigenetic priming will overcome them. [R3]')
h('The chain that must be tested')
table(['Evidence step','Question that remains to be answered'],[
 ['Clinical relevance','Is a programme associated with response, and in which cancer, regimen and endpoint?'],
 ['Prostate regulation','Is the prostate deficit regulatory, compositional, genetic, or a mixture?'],
 ['Molecular responsiveness','Does a perturbation move the programme in the intended direction?'],
 ['Functional consequence','Does the change improve a measured immune function rather than only a marker?'],
 ['Exposure and timing','Is the relevant effect compatible with the measured exposure, duration and uncertainty?'],
],[.28,.72])
callout('The thesis is strongest when it identifies both where the chain is supported and where it breaks. A null perturbation result, a weak model, or non-identifiable timing can be a valid scientific conclusion.')
source('S2-S14; representative biological rationale R1-R3, not a systematic literature review')

section('03 | Paper A','The baseline clinical reference')
p('<b>Aim.</b> Identify pretreatment immune-expression programmes reproducibly associated with objective ICI response, and assess how well one frozen learned score discriminates response in independent studies. The clinical evidence is not automatically prostate-specific.')
h('Scope: one paper, two distinct products')
p('<b>A-BIO</b> produces a biological reference: effects, uncertainty, cancer/regimen context, stability and contradictory evidence. <b>A-PRED</b> produces a frozen predictive score and a transparently labelled independent evaluation. A useful biological finding does not require the learned predictor to outperform the comparator.')
h('The selected primary and its meaning')
callout('<b>A-P2:</b> learned-score AUROC minus fixed-CYT AUROC, evaluated on the <b>same</b> ORR-evaluable independent-test patients. Summaries give equal weight to cancers, then equal weight to originating studies within cancer.')
p('AUROC measures discrimination: how well a score orders responders above nonresponders. The paired comparison prevents the models from being judged on different patients. Equal cancer/study weighting prevents the largest contributing cancer or study from silently defining the whole result. It is not a measure of treatment benefit or calibration.')
p('<b>A-P1 is secondary and CYT-led.</b> It asks how discrimination changes when response is defined as disease control rather than objective response, using the same fixed score and eligible patients. It preserves complete/partial response, stable disease and progression categories. A learned-score version is additional, not the controlling hierarchy.')
h('Intended outputs')
p('A source-audited baseline analysis matrix; programme/gene effect tables and uncertainty; context and contradiction summaries; a frozen score with features, coefficients and transformations; independent A-P2 results; endpoint-sensitivity results; and a versioned A-BIO handoff to B/C. These outputs are complementary, not interchangeable.')
h('What the paper contributes - and cannot establish')
p('A supplies the clinical rationale for asking about particular immune functions in B/C. Association direction must be distinguished from the sign of a penalized prediction coefficient. Clinical response association does not prove a tumour-cell mechanism, epigenetic reversibility, an ICI treatment effect, or efficacy in prostate cancer.')
p('<b>Release boundary:</b> real datasets, model settings and independent-test membership require their own releases. Missing final-test data blocks A-P2 evaluation, not every valid A-BIO or A-P1 branch. Reserved test families remain protected across all papers.')
source('S3, S4, S2')

section('04 | Paper A.1','The longitudinal response-associated view')
p('<b>Aim.</b> Determine which immune-expression programmes change during treatment, whether within-patient changes differ between eventual responders and nonresponders, and which regimen, sequence and timing differences can actually be identified from the data.')
callout('<b>Core contrast:</b><br/>Average follow-up minus baseline change in responders<br/><b>minus</b><br/>Average follow-up minus baseline change in nonresponders.')
p('This is a difference in <b>observed changes</b>, not a randomized treatment effect. Treatment selection, follow-up availability, timing, prior therapy and response classification can affect the comparison. A cross-sectional comparison of on-treatment responders and nonresponders answers a different question.')
h('Scope and inputs')
p('A.1 uses source-qualified baseline/follow-up pairs, exact patient and treatment-episode identities, timepoint definitions, assay compatibility and outcome bindings. It consumes the shared DAV registries rather than building another patient list. Numeric windows and analysis settings remain release items where not yet settled.')
p('Pairing, within-study estimation, cross-study synthesis, each moderator and manuscript promotion have separate gates. A valid study-specific estimate is not blocked merely because a broader drug-class comparison is unidentifiable. Clinical network meta-analysis is not an automatic requirement.')
h('Intended outputs')
p('A longitudinal pair matrix; a timepoint and selection audit; study-level response-associated change estimates with uncertainty; compatible-study summaries; explicitly qualified moderator results; and <b>longitudinal_support.tsv</b> with versioned provenance. Missing paired methylation or spatial data need not block qualified RNA analyses.')
h('Its role in the ecosystem')
p('A provides a baseline reference; A.1 asks whether relevant programmes move over time. This can contextualize B/C hypotheses and D/E model assumptions, but observational change must not be inserted directly as a causal kinetic rate. Baseline and longitudinal results from the same patients are related evidence, not independent replication.')
p('<b>Publication status:</b> A.1 is an active, specified thesis workstream. Thesis inclusion is the default; a separate manuscript depends on distinct evidence and adequate precision, not on a significant result. The directory does not promise a second publication or prove external preregistration.')
source('S5, S2')

section('05 | Paper B','Prostate immune deficits and epigenetic context')
p('<b>Aim.</b> Investigate which clinically relevant immune functions are deficient in defined prostate tumour contexts, which deficits have reproducible epigenetic correlates, and which candidates justify restoration testing. B is the patient molecular chapter linking the clinical reference to prostate biology.')
h('Two levels must remain distinguishable')
p('The <b>approved broad aim</b> includes immune deficits, regulatory evidence, composition alternatives and candidates for C. Within it, the fixed <b>APM B-P module</b> has a selected molecular-validation endpoint. The more detailed September 28 revision remains a proposal; it is not an accepted replacement for B-P.')
callout('<b>B-P:</b> external Delta R-squared = (baseline prediction error sum of squares - extended prediction error sum of squares) / total outcome variation, evaluated in locked CPC-GENE using models fitted in TCGA.')
p('The baseline uses declared clinical/purity covariates; the extended model adds the specified methylation information. A positive contrast means lower external prediction error on the declared molecular endpoint. It is not an improvement in patient survival or ICI response. Exact programme membership, annotation universe, specimen policy and measurement settings still need their releases.')
h('Scope and intended outputs')
p('Inputs include appropriately linked prostate expression, methylation, clinical and cellularity information, plus qualified contextual evidence. Outputs include programme-specific deficit estimates; methylation-expression associations; composition and other sensitivity analyses; frozen baseline/extended predictors and external errors; and a discovery-only candidate/query handoff to C.')
p('The C handoff separates an expression-only query from a methylation-supported query. It preserves direction, effect uncertainty, source patients, regulatory evidence and alternative explanations. CPC evaluation outcomes must not be used to select a supposedly discovery-only query.')
h('Scientific interpretation')
p('Low bulk expression can reflect fewer relevant cells, altered expression within cells, or both. Methylation associations can accompany regulation without proving causal silencing. APM is one immune function; success in that module does not establish the entire immune-barrier hypothesis. A single all-positive composite would hide these distinctions.')
p('<b>Implementation status at RC2:</b> B has preserved W1-W8 synthetic software. Real-cohort validation is not established. The integration regression retained a missing real-format fixture failure; synthetic passing tests cannot resolve specimen linkage or validate biology.')
source('S6, S7, S15')

section('06 | Paper C','From regulatory evidence to perturbation priorities')
p('<b>Aim.</b> Test whether clinically anchored, methylation-supported prostate immune-barrier queries show greater desired-direction molecular responsiveness than matched expression-only queries, and prioritize interventions while retaining mechanism, cellular context, viability and pharmacology.')
h('The accepted architecture')
p('<b>C3</b> is evidence-based experimental prioritisation. <b>C2</b> is a bounded, identity-curated discovery screen. <b>C1</b> is secondary calibration. The old three-compound connectivity primary must not be restored. The paired measured endpoint is a proposed primary contract, not an analysis release.')
callout('<b>Q_M versus Q_E:</b> matched methylation-supported and expression-only queries use the same discovery framework and programme/direction quotas. Their desired-state scores are compared <b>within measured biological samples</b>, then between treatment and control.')
p('For each sample, D = score(Q_M) - score(Q_E). A source-specific treatment contrast estimates whether treatment shifts Q_M more than Q_E. One originating-study contribution enters the source-equal summary, Delta_Q. Report both component effects: a relative advantage is not restoration if both queries move in the wrong direction.')
h('Scope and outputs')
p('Inputs comprise frozen B queries, curated compound identities, bounded perturbation resources and separately designated independent measured experiments. The scoring contract uses the full measured gene universe, declared directions and pinned numerical implementation. Genes, wells or cells must not be counted as independent biological experiments.')
p('Outputs include query/scorer-parity receipts; a curated candidate universe; context-, dose- and time-labelled discovery evidence; paired measured effects and uncertainty; coverage/replication audits; evidence tiers or a Pareto set of candidates; and a prospective experimental handoff. A Pareto set retains trade-offs instead of inventing one universal score.')
h('What counts as evidence')
p('A connectivity rank supports a hypothesis about expression change. Independent measured evidence tests molecular responsiveness. Neither alone establishes tumour killing, checkpoint synergy, comparative clinical efficacy or an achievable kinetic rate. Viability effects and exposure plausibility must remain separately visible.')
p('<b>Pending gates:</b> query release, source independence, scorer parity and numerical analysis choices. Coverage and replication numbers appearing in the draft are proposals requiring outcome-blind confirmation, not newly approved defaults in this guide.')
source('S8, S9, S2')

section('07 | Paper D','Predictive models with measured benchmarks')
p('<b>Aim.</b> Test whether explicitly defined models predict independently measured prostate perturbation or tumour-T-cell behaviour better than appropriate baselines. D is a model-evaluation programme, not a claim that a virtual tumour already reproduces a patient.')
h('D1: the conditional molecular benchmark')
p('D1 compares a frozen virtual-cell perturbation model against a fixed mean-response comparator for the same supported drug, dose and duration. The test uses the complete ordered checkpoint output gene space and compatible measured prostate responses. Missing compatible comparator contexts block the condition; nearest-dose substitutions are not allowed.')
callout('<b>D1 theta:</b> baseline squared-error loss minus model squared-error loss, averaged equally across drugs, then eligible conditions, then independent biological units. Positive theta favours the model. Report both losses, not only the difference.')
p('The exact gene space, measurement scale and weights matter: changing them changes the scientific question. A large number of cells cannot substitute for independent biological replication. Secondary programme/direction and failure analyses are needed because global expression error alone is incomplete.')
h('D2-PAIR: a minimal tumour-T-cell system')
p('D2 begins with measured drivers and qualified functional observations. It compares a calibrated spatial model against a nonspatial count/ODE model and a minimal rule-only spatial baseline. A preferred held-out endpoint is specific viable tumour loss or count at a qualified timepoint, but promoting D2 to primary requires an explicit amendment before confirmatory outcomes are inspected.')
p('<b>D2 does not depend on D1 winning.</b> Learned molecular coupling is a later, separate branch that requires both an accepted molecular model and a validated molecular-to-phenotype bridge. Unsupported cell types or processes must remain absent or labelled unsupported.')
h('Intended outputs and limits')
p('D1 outputs a compatibility audit, frozen benchmark, losses and uncertainty, and failure/coverage analysis. D2 outputs a measured-driver model, calibrated parameters, independent functional predictions, baseline comparisons and uncertainty. A combined paper must not claim that validating one module validates the other.')
p('A tumour-T-cell pair is not a full tumour microenvironment. D cannot manufacture B-cell/TLS outputs, establish clinical sensitisation from monoculture markers, or claim a patient-specific digital twin. An informative negative benchmark remains a possible contribution.')
source('S10, S11')

section('08 | Paper E','Public evidence, exposure and treatment timing')
p('<b>Aim.</b> Determine which timing conclusions are supported by recoverable public exposure, pharmacodynamic and immune evidence; which conclusions change under admissible uncertainty; and which remain non-identifiable. No sequence is assumed to be best.')
h('Three scientific levels')
table(['Level','Role'],[
 ['E1: exposure and priming kinetics','PBPK/PK and PD describe exposure, target engagement and relevant priming dynamics using qualified evidence.'],
 ['E2: reduced tumour-immune QSP','A limited mechanistic model connects supported dynamics to a specified functional context.'],
 ['E3: constrained sets / ensembles','Examine which parameterisations and structures fit the evidence, and whether schedule conclusions persist.'],
],[.31,.69])
p('These E1-E3 scientific levels are different from the E0-E7 implementation packet IDs. The public core must work with E_LAST and all internal observations absent. D completion is not a prerequisite.')
h('The proposed estimand')
callout('For each schedule, J is time-averaged modelled tumour burden relative to a common baseline. Delta = J(epigenetic-first) - J(concurrent). The target is the <b>set of Delta values compatible with the admitted evidence and model contracts</b>, not one hand-picked simulation.')
p('Negative Delta favours the epigenetic-first schedule on this model endpoint. Comparisons use fair dose and time accounting, including the lead-in period. Dose matching does not imply exposure matching. Compound, antibody, schedules, horizon and tolerances still require recorded decisions.')
h('Intended outputs and two completion profiles')
p('Outputs include public source/model inventories, exposure and PD checks, an executable reduced QSP system, evidence-constrained parameter/structure sets, schedule-contrast results, uncertainty decomposition and missing-measurement priorities.')
p('<b>C-SCHEDULING</b> supports qualified conditional timing conclusions. <b>C-IDENTIFIABILITY</b> quantitatively demonstrates that available observations permit incompatible timing conclusions, and identifies measurements that could resolve them. The latter requires evidence-linked analysis, not a toy illustration or a failed optimiser.')
p('These are research model conclusions, not dosing advice, patient-specific recommendations or clinical efficacy. Simulated individuals and timepoints do not create independent biological sample sizes.')
source('S12, S13')

section('09 | E_LAST','An optional experiment-informed extension')
p('<b>Aim.</b> Test whether the accepted public-evidence E foundation transfers to the actual local system, what additional parameters new observations can identify, and whether frozen predictions agree with independent measurements.')
callout('<b>Entry condition:</b> an immutable, accepted E-core release <b>plus</b> admitted original observations and applicable approvals. E_LAST is not a hidden prerequisite for completing E core.')
h('What it can add')
table(['Use of new observations','Scientific meaning'],[
 ['Calibration','Estimate or constrain parameters for a new model version. Agreement with those same observations is fit, not independent validation.'],
 ['Retrospective evaluation','Assess a frozen prediction against observations not used to construct that version, with prior exposure disclosed.'],
 ['Prospective validation','Freeze the prediction and analysis before the qualifying new outcome is observed.'],
 ['Descriptive bridge','Document compatibility or mismatch when the evidence supports neither calibration nor independent validation.'],
],[.29,.71])
p('The extension keeps donor/experiment identity, biological replication, assay units, timing and source roles explicit. One observation cannot both calibrate and independently validate the same model version. Updating a model produces a new version rather than overwriting the public foundation.')
h('Intended outputs')
p('An extension activation/admission receipt; an exact foundation version; original-data provenance and roles; before/after predictions and uncertainty where updating is justified; calibration or evaluation results at their actual evidence level; and an explicit statement of claims gained and claims still unsupported.')
h('Place in the thesis')
p('E_LAST offers a route from public evidence to a qualified local measurement system. It may reveal that public priors transfer poorly, that a timing parameter becomes identifiable, or that a prediction fails. All are informative outcomes. It is an optional extension, not automatically a separate manuscript.')
p('D products and A-C context may be consumed only by approved branches through documented interfaces. A simulated D output does not become a measured E calibration observation. Experimental planning, access and ethical governance remain separate activities; this specification does not authorize new biological work.')
source('S14, S2')

section('10 | The shared foundation','DAV: what is actually being compared?')
p('The shared <b>data acquisition and validation</b> kit is infrastructure for A and A.1, not another paper. Its scientific purpose is to establish that records really refer to the intended studies, people, treatment episodes, samples, assays and outcomes before an analysis uses them.')
table(['Record or artifact','What it represents scientifically'],[
 ['Originating study / publication family','The underlying investigation and its related reports or reanalyses. Several papers or downloads may describe one source of evidence.'],
 ['Patient / treatment episode','The person and the specific course of treatment to which an outcome belongs. A patient can contribute more than one episode.'],
 ['Specimen / assay / source object','What biological material was measured, how it was measured, and which exact bytes supplied the result.'],
 ['Original / canonical outcome','The source-defined endpoint and its explicit harmonised representation; harmonisation must not invent stable disease or timing.'],
 ['Overlap / prior-exposure ledger','Shared people, samples or source families, and which information has already been accessed or used.'],
 ['Materialized matrices / receipts','The actual eligible rows for baseline, timepoint, pair and endpoint analyses, with exclusions, versions and hashes.'],
],[.32,.68])
h('Why treatment-episode binding is central')
p('Imagine a synthetic patient receiving treatment X, then treatment Y. A response measured during Y must not label a pretreatment sample intended for X. The episode-binding contract preserves that relationship even when source files share the same patient label. Syntactically valid identifiers alone cannot prove that the relationship is clinically correct.')
h('One registry, several released branches')
p('The same admitted source can support a baseline matrix and a longitudinal pair matrix under different eligibility rules. Shared identities prevent duplicate counting; branch-specific receipts prevent one successful admission check from being mistaken for universal analysis readiness. Patient-level records remain private by default.')
p('<b>Scientific payoff:</b> DAV protects the unit of analysis, endpoint meaning, temporality, cohort independence and test boundaries. The first bounded implementation packet uses synthetic records to test these safeguards; it does not admit real patients or execute a paper.')
source('S2, S16')

section('11 | Technical explanation','What the SpecKit is')
p('In this repository, <b>SpecKit</b> means the versioned collection of scientific specifications, data contracts, schemas, decisions, tests, implementation tickets and release evidence. It translates a research question into inspectable requirements for people and software. The name alone does not establish use of a particular external framework or CLI.')
callout('<b>Question → estimand → data/measurement contract → software interface → tests → release receipt → permitted scientific claim</b>')
h('Four layers work together')
table(['Layer','Technical representation','Scientific job'],[
 ['Human-readable design','Markdown aims, analysis plans, decisions and claim limits.','Explain why an analysis is justified and which alternatives remain unresolved.'],
 ['Machine-readable contracts','JSON schemas, registries, TSV tables and versioned configurations.','Make identity, units, missingness, roles and admissibility explicit.'],
 ['Executable verification','Synthetic fixtures, validators, regression and parity checks.','Detect implementation violations before they distort interpretation.'],
 ['Provenance and release','Hashes, source manifests, environment records, Git commits, freeze matrices and receipts.','Connect each claim to the exact evidence and analysis version that produced it.'],
],[.22,.38,.40])
h('How an implementation consumes the kit')
p('A bounded ticket selects an approved contract and its input/output schemas. The implementer reuses compatible code, adds behaviour tests and emits named artifacts. The reviewer checks scientific meaning as well as program behaviour. A release records which gates closed and which did not; it does not fill unknown values with convenient defaults.')
p('<b>Schema validation</b> answers whether a record has the declared structure. <b>Relational validation</b> checks whether records agree with one another. <b>Scientific admission</b> requires source evidence and appropriate review. These are separate checks: a JSON object can satisfy its schema while describing the wrong treatment episode.')
p('<b>Current scope:</b> the kit contains specifications and bounded reference/QA code, plus reusable existing A/B implementation. It is not proof that all pipelines, production simulators, cohorts or scientific results already exist.')
source('S1, S15-S18')

section('12 | SpecKit component map','Scientific design and evidence components')
p('Each component encodes a scientific choice or a protection against a specific interpretive error. The examples below are representative canonical files; they are not 696 separate research questions.')
table(['Part / representative example','Technical purpose','What it reflects scientifically'],[
 ['Aim and claim limits<br/>A/SCIENTIFIC_AIM_AND_CLAIMS.md','Names the question, target and permitted conclusions.','Separates association, prediction, mechanism and benefit; prevents a successful analysis from answering a larger, untested question.'],
 ['Decision / approval records<br/>docs/decisions/','Records selected choices, amendments and supersession.','Distinguishes accepted scientific design from an attractive proposal or historical alternative.'],
 ['Analysis / estimand contract<br/>C/.../ANALYSIS_CONTRACT.md','Defines comparison, outcome, weights, units of replication and inference.','States precisely what quantity the paper estimates and for whom it is meaningful.'],
 ['Data-source contract / manifest','Lists sources, versions, objects, permitted uses and gaps.','Defines the evidence base, independence and source limitations; discovery metadata is not dataset admission.'],
 ['Ontologies / dictionaries<br/>DAV/ENDPOINT_ONTOLOGY.md','Standardises identifiers, labels and mapping rules.','Preserves endpoint and measurement meaning across heterogeneous studies rather than equating similar names.'],
 ['Validation / split architecture','Defines development, evaluation, calibration and test roles.','Protects independence; a dataset used to choose the model cannot independently test that same choice.'],
 ['Figure and claim plan','Maps panels to source tables, estimands and claim levels.','Makes the argument inspectable; separates descriptive, fitted and independently evaluated results.'],
 ['Unresolved / numerical register','Keeps undecided settings and required evidence explicit.','Prevents code defaults from silently choosing cohorts, thresholds, endpoints or statistical assumptions.'],
],[.30,.28,.42])
source('S3-S18')

section('13 | SpecKit component map','Engineering and governance components')
table(['Part / representative example','Technical purpose','What it reflects scientifically'],[
 ['JSON schemas<br/>DAV/schemas/episode_binding.schema.json','Specify required fields, types and allowed states.','Operational definitions: what must be known to call a row an episode-linked observation. Structure alone does not verify truth.'],
 ['Registries / templates / matrices','Create stable keys, row grain and analysis-ready table layouts.','Specify what one row represents: patient, specimen, pair, experiment or PK aggregate. These units must not be conflated.'],
 ['Lineage / overlap ledgers','Record transformations, shared sources and prior data use.','Expose dependence and selection history; prevent duplicate evidence and test leakage.'],
 ['Interfaces / handoff schemas','Define producer, consumer, fields, units, versions and allowed use.','Preserve the meaning of evidence across papers; a rank cannot silently become a rate constant.'],
 ['Tests / synthetic fixtures','Exercise valid cases, missingness, ambiguity, mutation and failure.','Protect reasoning invariants. Passing a synthetic test validates behaviour in that test, not a biological hypothesis.'],
 ['Tickets / migration map','Bound the next code change and classify existing implementation.','Make scientific requirements implementable without rebuilding valid code or relaxing new safeguards.'],
 ['Environment / reproducibility','Pin dependencies, source hashes and exact commands.','Support computational repeatability; identical software does not resolve biased or inadequate data.'],
 ['Freeze manifest / receipts','Bind content to a version and document release gates.','Make the analysis lineage auditable; a hash proves identity, not correctness or approval.'],
 ['Handoff / agent prompts','State inputs, allowed writes, tests and stop conditions.','Constrain delegated work so coding agents cannot silently redefine the study.'],
],[.30,.29,.41])
source('S2, S15-S18')

section('14 | Interfaces','How papers exchange evidence safely')
p('A handoff is more than a file. It carries the artifact version, owner, source lineage, units, uncertainty, data roles, allowed uses and hashes. A consumer must know both what the value means and what it does not mean.')
table(['Producer → consumer','Valid transfer','Invalid interpretation'],[
 ['DAV → A / A.1','Admitted identities, episode bindings, matrices and branch receipts.','A downloadable matrix is automatically an admitted independent cohort.'],
 ['A-BIO → B / C','Context-labelled clinical associations and uncertainty from permitted development evidence.','A penalized score coefficient is a causal restoration direction.'],
 ['B → C','Frozen Q_M/Q_E queries with matched budgets, regulatory evidence and discovery lineage.','Methylation association guarantees drug reversibility; CPC outcomes may choose queries.'],
 ['C → downstream planning','Compound/context identities, measured effects, uncertainty and independent evidence roles.','Connectivity is clinical efficacy, a pharmacological rate or independent evidence for a model trained on it.'],
 ['D ↔ E where qualified','Explicit prediction products or exposure trajectories with scale, time basis and uncertainty.','A D prediction is a measured E calibration observation; E always requires D.'],
 ['E → E_LAST','Immutable public foundation and its limitations, then separately admitted observations.','Local calibration validates the unchanged public model or overwrites its evidence history.'],
],[.21,.41,.38])
h('When a handoff becomes invalid')
p('A change in source identity, feature membership/order, preprocessing, treatment role, units or fitted parameters can invalidate dependent artifacts. Versioned hashes and migration tests make this visible. The response is a documented new version and re-review, not silently updating a frozen file.')
p('Shared clinical identity primitives are useful, but a patient, cell experiment, perturbation signature and PK summary have different statistical units. The ecosystem uses explicit adapters rather than forcing them all into one universal patient table.')
source('S2, S9, S14, S16')

section('15 | Worked conceptual example','Following one candidate through the ecosystem')
callout('<b>Illustrative reasoning only.</b> The programme below is hypothetical. It is not a selected gene set, observed result, approved drug or recommendation.')
table(['Step','Suppose the evidence says...','Then the defensible next question is...'],[
 ['A','An antigen-presentation-related programme is associated with ICI response in qualified clinical cohorts.','Does that association transport to the prostate context, and is it stable across studies?'],
 ['A.1','The same programme changes over treatment in a response-associated manner.','Is this compatible longitudinal support, or does timing/selection offer another explanation?'],
 ['B','A prostate subgroup shows lower expression with accompanying methylation evidence.','Is the apparent deficit explained by cell composition or other factors? Does the evidence justify a frozen candidate query?'],
 ['C','An admitted perturbation changes the methylation-supported query more than its matched comparator.','Do the absolute component effects show restoration? Are the result, context, viability and exposure credible?'],
 ['D','A model predicts compatible measured responses or qualified tumour-T-cell outcomes.','Does it beat the declared baselines on held-out evidence, and where does it fail?'],
 ['E','Several models fit public data but disagree about the best timing.','Which additional measurement would distinguish their predictions? Do data support any robust schedule conclusion?'],
 ['E_LAST','An independent new measurement disagrees with the frozen prediction.','Which assumption or parameter needs a new version, and what claim must be withdrawn or narrowed?'],
],[.12,.43,.45])
h('The inference is not automatic')
p('No row licenses skipping the next evidence requirement. A high A-PRED AUROC cannot replace B regulatory evidence. A positive C contrast cannot replace immune-function measurements. A successful model fit cannot establish prospective accuracy. The scientific contribution is the traceable evaluation of those links, including contradictions.')
source('S2-S14; hypothetical example constructed for explanation')

section('16 | Releases and readiness','Four releases, four different meanings')
table(['Release','What is frozen or accepted','What it does not imply'],[
 ['S: specification','Versioned architecture, decisions, interfaces, schemas, tickets and explicit pending gates.','Real data exist, proposed choices are approved, or biology has been validated.'],
 ['D: data','Admitted objects, identities, units, coverage, overlap and role assignments.','The statistical analysis or final-test access is authorized.'],
 ['A: analysis','Exact estimand, settings, model/query version, independence and numerical decisions.','Jobs have run successfully or results are accepted.'],
 ['X: execution / results','Permitted environment/jobs, immutable outputs and reviewed results.','Every scientific claim or clinical application is justified.'],
],[.21,.42,.37])
p('<b>RC2 is an S-level candidate with pending gates.</b> B revision details remain unadopted; C has an approved framework but a proposed primary analysis release; D2 primary promotion is amendment-gated; E scheduling choices and evidence releases remain pending. These statuses can differ within a paper.')
h('What the integration checks demonstrated')
p('The integration verified scoped file identity and ran specification, schema and synthetic/reference checks. It preserved existing A/B code. B\'s strict regression was not completely green: a real-format fixture was missing, and a sandbox socket error was separately resolved by a passing subset. None of these checks measured a biological treatment effect.')
h('Why the packaging correction matters')
p('RC1 omitted six E Markdown contracts from its committed tree because of an ignore rule, despite their presence on disk. RC2 restored them and added Git-content verification. This illustrates why a local file, a manifest entry and a remotely published artifact are three separate facts to verify.')
h('How future work stays within scope')
p('Each implementation packet uses a separate Luna chat, independent Sol 6.1 review and Astra Low closure. Frozen scientific choices cannot change silently; substantive amendments require explicit approval and a new version. Preparation can proceed around unrelated blockers, but no production analysis follows automatically from passing software checks.')
source('S1, S15, S17, S18')

section('17 | Thesis synthesis','What this ecosystem can contribute')
p('The programme is designed to produce an auditable account of <b>where epigenetic priming is plausible, what evidence supports it, which contexts limit it, and which measurements are still needed</b>. It does not assume that every paper will produce a positive result or that every layer must be combined into one score.')
h('A connected scientific argument')
p('A/A.1 establish clinical and temporal relevance. B asks whether corresponding prostate states have regulatory support after considering alternatives. C tests the incremental value of that support in measured perturbation evidence. D evaluates whether selected response models add predictive information. E assesses whether timing conclusions survive pharmacological and structural uncertainty. E_LAST can then test transfer to an independently measured local system.')
h('How different outcomes would change the conclusion')
table(['Possible outcome','Scientific interpretation'],[
 ['A-BIO informative; A-P2 does not beat CYT','Biological associations may still guide hypotheses. Added predictive superiority is unsupported.'],
 ['B methylation adds no external information','The specified molecular-prediction claim is not supported; descriptive or regulatory evidence must be judged separately.'],
 ['C finds no Q_M advantage','Methylation support did not improve the declared paired responsiveness contrast. Do not select a new primary after seeing results.'],
 ['D model fails against a strong baseline','The model may not add useful prediction in that domain. Measured-driver D2 remains separately assessable.'],
 ['E timing is non-identifiable','Public evidence cannot distinguish the declared schedules; a quantitative measurement-priority result can still complete the appropriate profile.'],
 ['E_LAST fails transfer','The local system exposes a domain or model limitation, requiring honest revision rather than relabelling the test.'],
],[.39,.61])
callout('<b>Proposed thesis contribution:</b> a structured, uncertainty-aware investigation of the links between clinical immune relevance, prostate epigenetic regulation, molecular responsiveness, functional prediction and treatment timing. Clinical sensitisation remains a separate empirical claim, not the sum of these papers by definition.')
source('S3-S15; synthesis is an interpretation of the specified programme')

section('18 | Reading vocabulary','A short glossary')
table(['Term','Meaning in this guide'],[
 ['Epigenetic priming','A hypothesised change in regulatory state intended to alter later immune responsiveness; the effect must be measured in its context.'],
 ['ICI / checkpoint blockade','Immune checkpoint inhibitor treatment; a specific clinical or experimental intervention, not a generic synonym for immune activation.'],
 ['APM / CYT','APM: antigen-processing/presentation machinery. CYT: the fixed cytolytic expression comparator, using the qualified GZMA/PRF1 abundance contract in A.'],
 ['ORR / DCR','Objective response and disease control definitions. In A-P1, disease control additionally includes qualified stable disease; source criteria and timing remain essential.'],
 ['Estimand','The precisely defined quantity to be estimated: population, outcome, contrast, weighting and interpretation.'],
 ['AUROC / Delta R-squared','Discrimination of a binary endpoint / incremental external molecular prediction performance. Neither directly measures clinical treatment benefit.'],
 ['Confounding / composition','Alternative explanations for associations; bulk measurements can change because cell proportions change, not only because expression within cells changes.'],
 ['PK / PBPK / PD','Pharmacokinetics / physiologically based pharmacokinetics / pharmacodynamics: exposure, its physiological representation, and exposure-related effects.'],
 ['QSP / ODE','Quantitative systems pharmacology / ordinary differential equation: model frameworks for specified dynamic mechanisms.'],
 ['Identifiability','Whether the available observations can distinguish the parameter, mechanism or schedule contrast being claimed.'],
 ['Calibration / validation / leakage','Fitting to data / testing a specified claim using appropriately independent evidence / information crossing a protected development-test boundary.'],
 ['Schema / provenance / hash','Machine-readable structural rules / the record of where evidence came from and how it was used / a fingerprint of exact bytes.'],
 ['RC / gate / amendment','Release candidate / a required condition for a specific stage / a documented approved change with a new version and downstream review.'],
],[.31,.69])

section('19 | Canonical source map','Specification sources: papers and interfaces')
p('All S references below point to immutable files at the RC2 snapshot. They document the intended study design and its authority; they are not evidence that the studies have been executed. Paper-specific pages cite the controlling entries and the analysis contracts used for this guide.','small')
spec_refs=[
 ('S1','Programme entry and authority','START_HERE.md','docs/integration/20261015/AUTHORITY_AND_SUPERSESSION.md'),
 ('S2','Cross-paper interfaces and lineage','docs/integration/20261015/CROSS_PAPER_INTERFACES.md','docs/integration/20261015/DATA_AND_EXPERIMENT_LINEAGE.md'),
 ('S3','Paper A scope and claims','specs/A/README.md','specs/A/SCIENTIFIC_AIM_AND_CLAIMS.md'),
 ('S4','Paper A prediction and endpoint sensitivity','specs/A/PREDICTION_ANALYSIS.md','specs/A/ENDPOINT_SENSITIVITY.md'),
 ('S5','Paper A.1 scope and longitudinal analysis','specs/A1/README.md','specs/A1/LONGITUDINAL_ANALYSIS.md'),
 ('S6','Paper B scope and fixed analysis','specs/B/README.md','specs/B/ANALYSIS.md'),
 ('S7','Paper B broad framework and proposal status','specs/B/IMMUNE_BARRIER_FRAMEWORK.md','specs/B/SCIENTIFIC_REVISION_REVIEW.md'),
 ('S8','Paper C framework and analysis contract','specs/C/revision_20261015/README.md','specs/C/revision_20261015/ANALYSIS_CONTRACT.md'),
 ('S9','B-to-C query and validation contracts','specs/C/revision_20261015/QUERY_HANDOFF.md','specs/C/revision_20261015/VALIDATION_ARCHITECTURE.md'),
 ('S10','Paper D scope and endpoints','specs/D/revision_20261015/README.md','specs/D/revision_20261015/ANALYSIS_AND_ENDPOINTS.md'),
 ('S11','Paper D accepted amended decisions','specs/D/revision_20261015/DECISIONS_DA_DH.md','docs/integration/20261015/source_package_notes/Paper_D_Decision_Spec_Kit_v1_20261015/APPROVAL_RECORD.md'),
 ('S12','Paper E scope and completion profiles','specs/E/README.md','specs/E/CORE_COMPLETION_CONTRACT.md'),
 ('S13','Paper E proposed estimand and claim ladder','specs/E/inference/PRIMARY_ESTIMAND_AND_ANALYSIS.md','specs/E/CONTEXT_OF_USE_AND_CLAIMS.md'),
 ('S14','E_LAST scope and calibration/validation','specs/E_LAST/README.md','specs/E_LAST/CALIBRATION_VALIDATION_AND_PRIMARY.md'),
]
for sid,title,*paths in spec_refs:
    links=' | '.join(f'<link href="{BASE+path}" color="#007D83">{("Entry / first contract" if i==0 else "Companion / second contract")}</link>' for i,path in enumerate(paths))
    p(f'<b>{sid}. {title}</b><br/>{links}','small')
p('Links are bound to commit 92f9099c1a2e5442590729cce6d54f1a81958f27, not a moving branch. If repository access changes, the same paths are in the local integration checkout and verified RC2 handoff bundle.','small')

section('20 | Source and interpretation notes','Technical sources and scientific background')
more_refs=[
 ('S15','Reconciliation and validation evidence','docs/integration/20261015/SPEC_TO_CODE_RECONCILIATION.tsv','docs/integration/20261015/VALIDATION_REPORT.md'),
 ('S16','Shared acquisition authority and outputs','specs/A_DATA_ACQUISITION_VALIDATION/README.md','specs/A_DATA_ACQUISITION_VALIDATION/OUTPUT_AND_SCHEMA_INDEX.md'),
 ('S17','Freeze matrix and RC2 manifest','docs/integration/20261015/FREEZE_MATRIX.tsv','docs/integration/20261015/FREEZE_MANIFEST.json'),
 ('S18','Implementation packet and technical architecture','docs/integration/20261015/CODEX_NEXT_PACKET_PROMPT.txt','specs/E/delivery/SOFTWARE_ARCHITECTURE.md'),
]
for sid,title,*paths in more_refs:
    links=' | '.join(f'<link href="{BASE+path}" color="#007D83">{("First source" if i==0 else "Companion source")}</link>' for i,path in enumerate(paths))
    p(f'<b>{sid}. {title}</b><br/>{links}','small')
h('Selected primary scientific references')
p('<b>R1.</b> Chiappinelli KB et al. Inhibiting DNA Methylation Causes an Interferon Response in Cancer via dsRNA Including Endogenous Retroviruses. <i>Cell</i> (2015). DOI: <link href="https://doi.org/10.1016/j.cell.2015.07.011" color="#007D83">10.1016/j.cell.2015.07.011</link>. <link href="https://pubmed.ncbi.nlm.nih.gov/26317466/" color="#007D83">PubMed record</link>. Mechanistic rationale in the studied systems; not a prostate clinical efficacy result.','small')
p('<b>R2.</b> Guo H et al. DNA hypomethylation silences anti-tumor immune genes in early prostate cancer and CTCs. <i>Cell</i> 186 (2023): 2765-2782.e28. DOI: <link href="https://doi.org/10.1016/j.cell.2023.05.028" color="#007D83">10.1016/j.cell.2023.05.028</link>. <link href="https://pubmed.ncbi.nlm.nih.gov/37327786/" color="#007D83">PubMed record</link>. Supports context-sensitive interpretation of epigenetic regulation.','small')
p('<b>R3.</b> Antonarakis ES et al. Pembrolizumab for Treatment-Refractory Metastatic Castration-Resistant Prostate Cancer: Multicohort, Open-Label Phase II KEYNOTE-199 Study. <i>Journal of Clinical Oncology</i> 38 (2020): 395-405. DOI: <link href="https://doi.org/10.1200/JCO.19.01638" color="#007D83">10.1200/JCO.19.01638</link>. <link href="https://pmc.ncbi.nlm.nih.gov/articles/PMC7186583/" color="#007D83">Full-text record</link>. Clinical context for the rationale, not evidence for the thesis combination hypothesis.','small')
h('How this guide was prepared')
p('The canonical RC2 files were read and checked against their scoped SHA-256 manifest. The paper descriptions preserve the approved/proposed distinction, source independence, negative-result pathways and public-core/optional-extension separation. The references here provide representative background; the amendment appendix adds source checks for immune programmes. This document is not a systematic review, treatment recommendation or novelty clearance. Web records were checked on 16 October 2026.','small')
p('The ecosystem diagram and hypothetical example are explanatory syntheses. No patient records, private measurements, results, new thresholds, drug choices or approvals were introduced. Frozen RC2 files were not edited; the new amendment is an additive versioned layer. The PDF was generated separately, rendered for visual inspection and checked for page structure and source-link presence.','small')

section('21 | Approved amendment scope','Immune programmes across A, A.1 and B')
p('The user authorized this amendment on 16 October 2026: make antigen presentation, HOPE, immune evasion, immune-cell composition and tumour-microenvironment programmes explicit in A/A.1; align Paper B; verify original gene sets and scoring; preserve RC2; and do not run biological analysis.')
callout('<b>Two distinct statuses:</b> the expanded scientific scope is authorized. A source-verified gene list is not automatically an execution-ready score. Assay compatibility, numerical rules, cohort admission and statistical release remain separate gates.')
table(['Component','Scientific meaning and use'],[
 ['Antigen presentation','Separate MHC-I processing/presentation from MHC-II programmes. Expression is evidence of a programme, not a direct assay of functional peptide presentation.'],
 ['Inflammation and cytotoxicity','Retain recruitment/IFN responses, published T-cell-inflamed profiles and fixed CYT as distinct measurements. They overlap biologically but are not interchangeable.'],
 ['T-cell differentiation','Distinguish activation, progenitor-like states, effector/memory programmes and terminal dysfunction. A checkpoint or TCF7 alone does not identify a functional cell state.'],
 ['Immune evasion','Describe distinct barriers: presentation defects, inhibitory signalling, suppressive myeloid/Treg programmes, stromal/exclusion signals and immunometabolism. Do not average all mechanisms into an unexplained universal score.'],
 ['Cell composition','Use qualified bulk deconvolution to estimate represented populations. Preserve reference, scale, uncertainty and identifiability limits.'],
 ['Epigenetic context','In B, examine methylation-associated regulation alongside composition and genetic alternatives. Do not assign a universal direction to chromatin regulators.'],
],[.28,.72])
p('<b>A</b> examines baseline programmes and their clinical associations. <b>A.1</b> examines paired changes using compatible definitions and scales. <b>B</b> examines prostate molecular context and epigenetic associations. A-P2 and B-P remain the selected primaries; broader programmes do not become new co-primaries.')
p('RC2 remains available at its original tag and commit. The amendment has its own source ledger, membership/scoring registry, cross-paper contract and pending gates. It does not retroactively change what RC2 contained.','small')

section('22 | Original methods matter','Gene membership is only half a score')
p('The historical repository is useful evidence of intent, but its implementation is not an original-source authority. In particular, a mean of within-sample gene ranks must not be reported as ssGSEA, and a deprecated immune-score proxy must not be reported as ESTIMATE.')
table(['Panel or method','Verified distinction and consequence'],[
 ['APM18 / Wang','The original paper specifies 18 MHC-I processing/presentation genes and a GSVA score. This source-defined panel is separate from the thesis B-P target. Exact software parameters and assay qualification remain release requirements. [R12]'],
 ['CYT / Rooney','The original method uses GZMA and PRF1 TPM with a 0.01 offset. RC2 explicitly selected sqrt(GZMA x PRF1), without a pseudocount. Preserve that selected thesis variant and its primary endpoint; do not describe it as exact original-method reproduction. [R4]'],
 ['T-cell-inflamed GEP / Ayers','The final 18-gene profile uses a learned weighted scoring algorithm and assay normalization. A membership list or an unweighted average does not reproduce the published predictor. Inventor-disclosed weights were recovered as a candidate; equivalence to the published assay, normalization and platform transfer still require qualification. [R5, R14]'],
 ['HOPE 18-gene panel','The panel was selected for prognostic associations. It is not automatically an ICI-response predictor or a validated aggregate mean-expression score. Keep gene-level evidence separate from any proposed custom summary. [R6]'],
 ['HOPE immune classes','PD-L1/CD8B classification is a separate object from the 18-gene panel. The legacy cohort-median expression split is a relative proxy; it is not automatically a faithful reproduction of the publication. [R6]'],
 ['Custom and collection panels','Small local Hallmark-like and C7-like panels are custom subsets. Official collection names require exact release provenance. A biological interpretation does not justify relabelling a local gene list as an official collection.'],
],[.27,.73])
h('What each registry entry must preserve')
p('Exact symbols and identifier mapping; original source and location; species and biological compartment; published or custom status; required expression scale; algorithm and parameters; weights when applicable; missing-gene policy; version/hash; and claim limits. Coverage and transformation choices must be resolved before execution.')
p('Source-defined membership can be recorded now while a scoring implementation remains blocked. No missing coefficient, cutoff or gene is inferred from the legacy code or silently replaced with a convenient default.','small')

section('23 | TME interpretation','Four quadrants, several possible mechanisms')
p('The four-type framework combines PD-L1 status with T-cell infiltration. It is a useful organizing hypothesis, not a complete taxonomy of tumour immunity or proof of the mechanism behind an individual tumour. [R7]')
table(['Type','PD-L1 / TILs','Interpretation to investigate'],[
 ['I: adaptive resistance','Positive / present','An infiltrated state with inhibitory feedback; sometimes described as hot.'],
 ['II: ignorance','Negative / absent','Poor recruitment, recognition or both; sometimes described as cold.'],
 ['III: intrinsic resistance','Positive / absent','PD-L1 expression without corresponding infiltration; oncogenic causation requires additional evidence.'],
 ['IV: tolerance','Negative / present','Infiltration with ineffective immunity; non-PD-L1 suppressive mechanisms are possible, not established by the quadrant.'],
],[.28,.23,.49])
p('<b>Explicit crosswalk:</b> HOPE A maps to I; C to II; B to III; D to IV by matching sign patterns, with different operational measurements: HOPE uses CD274/CD8B RNA; Teng uses PD-L1/TIL status. Record the scheme, axes and measurement, not merely a letter or Roman numeral. [R6, R7]')
h('How this applies to bulk expression')
p('Retain continuous infiltration, checkpoint, presentation and suppression measurements. An expression-derived quadrant must be labelled a <b>transcriptomic TME proxy</b>. Bulk CD274 is not equivalent to tumour-cell PD-L1 protein positivity, and bulk T-cell signals do not reveal spatial localization. Missing or inadequate measurements require an indeterminate state, not a negative assignment.')
p('Do not choose thresholds by optimizing outcomes or recompute a different scale at each A.1 timepoint. A consistent longitudinal definition is essential before interpreting movement between states.')
h('Keep additional axes separate')
p('TMB is a mutation-derived quantity, not a gene-expression score or a synonym for neoantigen burden. High TMB does not define a hot tumour. TCGA/Thorsson C1-C6 immune subtypes are a different framework and have no automatic one-to-one mapping to these four quadrants. [R8]')
p('A quadrant does not select an effective drug combination. Epigenetic-agent effects depend on compound, dose, exposure, timing and cellular context; favourable immune modulation remains a hypothesis to test.','small')

section('24 | Data and cross-paper alignment','Cell composition and TCGA multiomics')
h('Cell typing: what is actually intended')
p('For admitted bulk RNA data, the planned analysis estimates cell composition using a qualified method and compatible reference. It does not label individual cells. ESTIMATE gives broad immune/stromal signals; enrichment scores are not cell fractions. Fine T-cell states and spatial exclusion require additional supporting evidence. [R9, R13]')
p('Availability of a historical expression file does not establish readiness. Each cohort still needs source linkage, assay units, compatible identifiers, adequate feature coverage, specimen rules and quality checks. Single-cell annotation requires actual admitted single-cell data. No new inventory or patient-level analysis is claimed here.')
table(['Paper','TCGA and composition role'],[
 ['A','TCGA-PRAD RNA provides untreated prostate molecular context and transportability checks. It is not an ICI-response test cohort. In treated clinical cohorts, composition helps interpret baseline programme associations.'],
 ['A.1','Use eligible longitudinal clinical pairs. Standard TCGA collections do not supply the required paired ICI design. A change in bulk programme score may reflect recruitment/composition, within-cell activity, or both.'],
 ['B','TCGA is the principal multiomics setting: RNA phenotypes and methylation associations, with qualified copy-number/mutation information, purity and clinical/pathological covariates as alternatives or context. Preserve external CPC-GENE evaluation and its protected boundary.'],
 ['C, D, E','Use qualified upstream outputs within their existing contracts. An expanded A/B panel does not automatically authorize new downstream endpoints, model calibration or treatment claims.'],
],[.17,.83])
p('TCGA prostate profiling includes expression, methylation, mutation and copy-number layers. Their joint use can distinguish competing explanations but does not make an observational relationship causal. [R10]')
h('A shared identity, not forced numerical comparability')
p('A, A.1 and B must exchange the exact programme/version, membership and scoring provenance. A common gene list does not make different assays numerically interchangeable. Never learn transformations on protected test outcomes or count an overlapping cohort twice as independent evidence.')

section('25 | Amendment sources and gates','What is settled, and what remains pending')
p('<b>Settled scope:</b> the expanded immune-programme framework and A/A.1/B alignment. <b>Preserved:</b> RC2 bytes and selected primaries. <b>Pending:</b> source-incomplete scoring bundles, custom membership/scoring approval where required, assay-specific qualification, numerical/statistical release, dataset admission and biological execution.')
p('The additive specification package is under <b>specs/amendments/2026-10-16-immune-programmes/</b>. Its <link href="https://github.com/OASolliman590/Master-Thesis-/blob/855384e5c8dcffc9d0863165b11486bf681905c5/specs/amendments/2026-10-16-immune-programmes/AMENDMENT.md" color="#007D83">reviewed amendment and source ledger</link> control the detailed status of each panel. This PDF is an explanatory companion, not a replacement for those contracts.','small')
refs=[
 ('R4','Rooney et al., Cell (2015). Original CYT definition and offset.','https://pmc.ncbi.nlm.nih.gov/articles/PMC4856474/'),
 ('R5','Ayers et al., JCI (2017). T-cell-inflamed gene-expression profiles and scoring.','https://www.jci.org/articles/view/91190'),
 ('R6','Kondou et al., Molecular and Clinical Oncology (2021). HOPE prognostic panel and immune classification.','https://www.spandidos-publications.com/10.3892/mco.2021.2395'),
 ('R7','Teng et al., Cancer Research (2015). Four-type tumour immune framework.','https://pmc.ncbi.nlm.nih.gov/articles/PMC4452411/'),
 ('R8','Thorsson et al., Immunity (2018). The Immune Landscape of Cancer.','https://doi.org/10.1016/j.immuni.2018.03.023'),
 ('R9','Newman et al., Nature Biotechnology (2019). CIBERSORTx digital cytometry.','https://www.nature.com/articles/s41587-019-0114-2'),
 ('R10','TCGA Research Network, Cell (2015). The Molecular Taxonomy of Primary Prostate Cancer.','https://pmc.ncbi.nlm.nih.gov/articles/PMC4695400/'),
 ('R11','Miller et al., Nature Immunology (2019). Distinct exhausted CD8 T-cell subsets and checkpoint response.','https://www.nature.com/articles/s41590-019-0312-6'),
 ('R12','Wang et al., eLife (2019). Antigen presentation and tumor immunogenicity in cancer immunotherapy response prediction.','https://cdn.elifesciences.org/articles/49020/elife-49020-v1.pdf'),
 ('R13','Yoshihara et al., Nature Communications (2013). ESTIMATE immune/stromal signals and tumour purity.','https://www.nature.com/articles/ncomms3612'),
 ('R14','Ayers et al., inventor disclosure US20180327848A1. Tables 3A/3B and 1C; candidate weights and normalization genes, not an admitted assay.','https://patents.google.com/patent/US20180327848A1/en'),
]
for rid,title,url in refs:p(f'<b>{rid}.</b> {title}<br/><link href="{url}" color="#007D83">Original source</link>','small')
p('TCF7-associated progenitor-like and terminally exhausted programmes should be interpreted as contextual states; one marker does not establish a functional identity. R11 provides primary experimental support for distinguishing these states.','small')
callout('<b>Execution boundary:</b> no cohort was admitted, no patient score or cell fraction was calculated, and no model or biological analysis was run for this amendment or guide. Specification checks establish contract consistency, not biological validity.')

class GuideCanvas(canvas.Canvas):
    def __init__(self,*args,**kw):canvas.Canvas.__init__(self,*args,**kw);self._saved=[]
    def showPage(self):self._saved.append(dict(self.__dict__));self._startPage()
    def save(self):
        n=len(self._saved)
        for state in self._saved:
            self.__dict__.update(state);self.footer(n);canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)
    def footer(self,n):
        self.setStrokeColor(colors.HexColor('#C9D7DD'));self.setLineWidth(.5);self.line(46,39,W-46,39)
        self.setFont('Body',7.5);self.setFillColor(MUTED);self.drawString(46,26,'THESIS GUIDE  |  RC2 + immune amendment  |  16 October 2026')
        self.drawRightString(W-46,26,f'{self._pageNumber:02d} / {n:02d}')
        if self._pageNumber>1:
            self.setFont('BodyBold',7.2);self.setFillColor(TEAL);self.drawString(46,H-28,'EPIGENETIC PRIMING  /  SCIENTIFIC & TECHNICAL GUIDE')
def first(c,doc):
    c.setTitle('Thesis Papers, SpecKit and the Epigenetic Priming Ecosystem')
    c.setAuthor('Thesis project - explanatory companion')
    c.setSubject('RC2 and additive A/A.1 immune-programme amendment with Paper B alignment')
doc=SimpleDocTemplate(str(OUT),pagesize=A4,rightMargin=46,leftMargin=46,topMargin=52,bottomMargin=55)
doc.build(story,onFirstPage=first,canvasmaker=GuideCanvas)
(TMP/'page_titles.json').write_text(json.dumps(page_titles,indent=2))
(TMP/'content_review.txt').write_text('\n\n'.join(content))
print(OUT)
print('Planned pages:',len(page_titles))
