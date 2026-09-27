"""Rebuild the corrected essay, presentation and supporting charts from rerun outputs."""
from pathlib import Path
import sys,json
from xml.sax.saxutils import escape
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from src.analysis import *
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,PageBreak,Image,Table,TableStyle,KeepTogether
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

OUT=ROOT/'outputs';FIG=ROOT/'figures';REP=ROOT/'reports'
for path in (OUT,FIG,REP):path.mkdir(exist_ok=True)
df=prepare_cohort(load_tables(ROOT/'data/raw'),'2024-10-04')
r=df[df.Num_Conditions.between(8,40)].copy()
models=pd.read_csv(OUT/'models.csv')
sex=summarise(r,['Cond_Bin','Gender']); age=summarise(r,['Age_Group','Cond_Bin'])
med=summarise(df,['Med_Bin']); race=summarise(r,['RACE','Cond_Bin'])
means=r.groupby(['Cond_Bin','Gender'],observed=True).agg(n=('Id','size'),mean_medications=('Num_Medications','mean'),mean_encounters=('Num_Encounters','mean')).reset_index()
major=summarise(r[r[['Has_'+n for n in MAJOR_RULES]].any(axis=1)],['Gender'])
for name,table in [('sex_summary',sex),('age_summary',age),('medication_summary',med),('race_summary',race),('history_means',means),('major_subset',major)]:table.to_csv(OUT/(name+'.csv'),index=False)
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.spines.top':False,'axes.spines.right':False,'figure.figsize':(9,4.6),'axes.titleweight':'bold'})
x=np.arange(3)
def bars(table,hue,items,file,title):
 fig,ax=plt.subplots(); width=.75/len(items)
 for j,(label,color) in enumerate(items):
  g=table[table[hue].astype(str).eq(label)].set_index('Cond_Bin').reindex(CONDITION_LABELS)
  ax.bar(x+(j-(len(items)-1)/2)*width,g.death_pct,width=width,label=label,color=color,
   yerr=np.vstack([np.maximum(0,g.death_pct-g.ci_low_pct),np.maximum(0,g.ci_high_pct-g.death_pct)]),capsize=4)
 ax.set(xticks=x,xticklabels=CONDITION_LABELS,xlabel='Distinct condition descriptions',ylabel='Recorded deaths (%)',title=title)
 ax.legend(frameon=False);fig.tight_layout();fig.savefig(FIG/file,dpi=190);plt.close(fig)
bars(sex,'Gender',[('Female','#b77aaa'),('Male','#7764aa')],'sex_current.png','Recorded sex and death status')
bars(age,'Age_Group',[('20-39','#b6d4e4'),('40-59','#5795bc'),('60-79','#193d62')],'age_current.png','Age at fixed reference date and death status')
fig,ax=plt.subplots()
ax.bar(med.Med_Bin.astype(str),med.death_pct,color='#79aeca',yerr=np.vstack([med.death_pct-med.ci_low_pct,med.ci_high_pct-med.death_pct]),capsize=4)
ax.set(xlabel='Distinct historical medication descriptions',ylabel='Recorded deaths (%)',title='Medication history in the full export')
fig.tight_layout();fig.savefig(FIG/'medication_current.png',dpi=190);plt.close(fig)
fig,ax=plt.subplots()
for offset,label,color in [(-.18,'Female','#b77aaa'),(.18,'Male','#7764aa')]:
 g=means[means.Gender.eq(label)]
 ax.bar(x+offset,g.mean_medications,width=.36,label=label,color=color)
ax.set(xticks=x,xticklabels=CONDITION_LABELS,xlabel='Distinct condition descriptions',ylabel='Mean distinct medication descriptions',title='Actual medication counts replace bin midpoints')
ax.legend(frameon=False);fig.tight_layout();fig.savefig(FIG/'medication_means.png',dpi=190);plt.close(fig)

def row(cohort,model,term):return models[(models.cohort==cohort)&(models.model==model)&(models.term==term)].iloc[0]
def orci(cohort,model,term,places=3):
 a=row(cohort,model,term);return f'{a.OR:.{places}f} ({a.ci_low:.{places}f}-{a.ci_high:.{places}f})'
def pformat(value):return '<0.001' if value<.001 else f'{value:.3f}'
model_compare=[['Predictor','Full export OR (95% CI)','Restricted OR (95% CI)']]
for label,term in [('Male vs female','C(Gender)[T.Male]'),('Age at reference, per year','Age'),('Condition count, per description','Num_Conditions')]:
 model_compare.append([label,orci('Full export','Age and sex adjusted',term),orci('8-40 descriptions','Age and sex adjusted',term)])
sex_test=pd.read_csv(OUT/'sex_tests.csv')
sex_table=[['Condition count','Female deaths / n','Male deaths / n','Ratio','Holm p']]
for label in CONDITION_LABELS:
 f=sex[(sex.Cond_Bin.astype(str)==label)&(sex.Gender=='Female')].iloc[0];m=sex[(sex.Cond_Bin.astype(str)==label)&(sex.Gender=='Male')].iloc[0];q=sex_test[sex_test.group==label].iloc[0]
 sex_table.append([label,f'{f.deaths} / {f.n}',f'{m.deaths} / {m.n}',f'{q.ratio:.2f}',f'{q.p_holm:.3f}'])
refs=[
 'Walonoski, J. et al. (2018). Synthea: An approach, method, and software mechanism for generating synthetic patients and the synthetic electronic health care record. Journal of the American Medical Informatics Association, 25(3), 230-238. https://doi.org/10.1093/jamia/ocx079',
 'Fortin, M., Stewart, M., Poitras, M.-E., Almirall, J. and Maddocks, H. (2012). A systematic review of prevalence studies on multimorbidity: toward a more uniform methodology. Annals of Family Medicine, 10(2), 142-151. https://doi.org/10.1370/afm.1337',
 'Crimmins, E.M., Shim, H. and Zhang, Y.S. (2019). Differences between men and women in mortality and the health dimensions of the morbidity process. Clinical Chemistry, 65(1), 135-145. https://doi.org/10.1373/clinchem.2018.288332',
 'Synthetic Health (2026). Synthea CSV File Data Dictionary. https://github.com/synthetichealth/synthea/wiki/CSV-File-Data-Dictionary (accessed 27 September 2026).',
]
# Ordered manuscript pages, with content retained as editable Markdown below.
pages=[
 {'heading':'Recorded condition burden and death status in synthetic Delaware EHR data','paragraphs':[
 'Bhakti Doshi | Health Data Science portfolio | Revised 27 September 2026',
 'Abstract',
 'This project examines associations between recorded condition burden, demographic characteristics and death status in a supplied Synthea export for Delaware. The full dataset contains 1,753 synthetic records, including 253 recorded deaths (14.43%). A sensitivity cohort reproduces the original assessment restriction to 8-40 distinct condition descriptions, retaining 1,716 records and 231 deaths (13.46%). Python joins patient, condition, medication and encounter tables, estimates death proportions with Wilson intervals, and fits retrospective logistic models.',
 'The restricted cohort has death proportions of 11.22%, 12.68% and 23.35% for 8-19, 20-29 and 30-40 condition descriptions. The age/sex-adjusted male-versus-female odds ratio is 1.835 in the restricted cohort and 1.836 in the full export. There is insufficient evidence of a sex-by-condition-count interaction on the log-odds scale in either cohort. The adjusted condition-count association differs between cohorts, highlighting sensitivity to exclusions.',
 'These results describe a simulator-generated record history. They do not establish why mortality differs between sexes, validate a clinical risk tool or estimate time-standardised mortality. The main contribution is a reproducible workflow with explicit cohort accounting, uncertainty estimates and transparent limits on interpretation.',
 'Research questions',
 'How does recorded condition burden relate to death status? Does the male-versus-female association persist after adjustment for age at a fixed reference date and condition count? Is there evidence that this association varies with condition count?',
 'Context',
 'Synthea produces realistic but synthetic health records (Walonoski et al., 2018). This permits a demonstration of EHR analysis without using clinical patient records. Operational definitions matter: multimorbidity prevalence varies with the diagnoses and definitions selected (Fortin et al., 2012). This project therefore uses the narrower term recorded condition burden for its history-based count.'
 ]},
 {'heading':'Methods and measurement','paragraphs':[
 'Data preparation',
 'The supplied export contains 107,376 condition rows, 191,649 medication rows and 173,900 encounter rows. The repository includes compressed extracts containing only analysis columns. Patient identifiers must be unique, foreign keys must resolve, and required fields and dates must pass validation. Source and extract hashes document provenance. The generator version, generation seed and official simulation end date were not supplied.',
 'The analysis uses 4 October 2024, the latest observed encounter start date, as a fixed reference date. This data-derived cutoff replaces the original notebook\'s changing computer date. Age at reference is elapsed time from birth to the cutoff. For deceased records, it is hypothetical attained age and functions as a birth-cohort covariate. It is not age at death. Death status indicates a recorded death on or before the cutoff.',
 'Exposure definitions',
 'Condition burden counts distinct diagnosis descriptions across recorded history. This includes historical and potentially non-chronic conditions, and does not establish concurrent chronic multimorbidity. The original numeric bins [8,20), [20,30) and [30,41) are preserved and correctly labelled 8-19, 20-29 and 30-40. Medication burden counts distinct historical medication descriptions, while utilisation counts encounter rows. Neither measure accounts for exposure time.',
 'The export\'s GENDER field contains F/M values. The analysis describes these recorded sex categories without inferring gender identity. Acute encounters comprise emergency, inpatient and urgent-care classes. Routine encounters comprise ambulatory, outpatient and wellness classes. Shares use acute plus routine encounters as the denominator and report other classes separately. A patient with no eligible encounters receives a missing share rather than zero.',
 'Statistical approach',
 'The full export is the primary descriptive cohort. The 8-40 subset is a sensitivity analysis that permits direct comparison with the assessment. Wilson intervals accompany proportions. Pearson chi-square tests compare death status by sex within condition strata, with Fisher\'s exact test available for sparse expected counts. Ratios of death proportions use Katz log intervals. Holm correction covers the three sex-stratum comparisons.',
 'Logistic models include an unadjusted condition-count model, an age/sex-adjusted model, a separate sex-by-centered-condition-count interaction model, and an exploratory model adding medication and encounter counts. Each model is fitted to both cohorts. The three acute-share comparisons use Mann-Whitney tests and their own Holm family. Routine shares are complementary and are not tested again. These are exploratory analyses with no held-out predictive validation.'
 ]},
 {'heading':'Cohort accounting and model sensitivity','paragraphs':[
 'The full cohort contains 878 male and 875 female records. Restricting condition counts to 8-40 excludes 37 records (2.11%), including 22 deaths (8.70% of all recorded deaths). The excluded group has a death proportion of 59.46%. The overall proportion falls by 0.97 percentage points, from 14.43% to 13.46%. Small cell sizes justify caution, but do not by themselves justify removal or demonstrate improved robustness.',
 'The unadjusted condition-count odds ratio is 1.019 per description in the full export (p = 0.035), compared with 1.039 in the restricted cohort (p < 0.001). After adjustment for age at reference and recorded sex, the full-cohort condition-count coefficient becomes inverse (OR 0.967, p = 0.002). In the restricted cohort it is 0.983 (p = 0.159). The latter does not reach a 5% threshold. This difference makes cohort choice material to the interpretation.',
 'Age/sex-adjusted models',
 ],'table':model_compare,'after':[
 'Both models show a positive male-versus-female association and a positive association with age at reference. A one-year coefficient should not be compared directly with a sex-category coefficient to rank predictor importance, because their units differ. Age at reference also does not mean age at death.',
 'In the fully adjusted exploratory model, condition-count odds ratios are 0.891 for the full export and 0.909 for the restricted cohort. Inverse coefficients do not show that accumulating diagnoses protects patients. Correlated histories, record length, survival time and conditioning on utilisation can contribute to the pattern. The model does not isolate any of those mechanisms.'
 ]},
 {'heading':'Condition burden and recorded sex','paragraphs':[
 'Within the restricted cohort, the 8-19 group has 83 deaths among 740 records (11.22%), the 20-29 group has 95 among 749 (12.68%), and the 30-40 group has 53 among 227 (23.35%). The highest group has a larger observed proportion, but three grouped estimates do not by themselves establish a nonlinear functional form.',
 ],'image':'sex_current.png','table':sex_table,'after':[
 'The corrected Holm p-values are 0.016, 0.037 and 0.037. All three comparisons remain below 0.05. The lowest-group ratio is 1.81, correcting the essay\'s 1.83. Groups with the same broad condition-count range may still differ in age, diagnoses and observation history.',
 'The separate interaction model gives OR 0.996 (95% CI 0.951-1.042, p = 0.847) in the restricted cohort and OR 1.004 (0.964-1.045, p = 0.855) in the full export. These results do not support the presentation\'s claim that increasing burden has a stronger effect in males. A nonsignificant interaction also does not prove identical effects, and this test concerns the log-odds scale rather than absolute differences in death proportions.'
 ]},
 {'heading':'Age, medication history and encounters','paragraphs':[
 'Age-stratified proportions generally increase across age bands within a burden stratum. However, these bands describe age at the fixed reference date, not age at death. The full export contains 25 recorded deaths before age 20, despite reference ages of approximately 30-75. It would be misleading to describe the dataset as deaths occurring only among adults aged 20-79.',
 ],'image':'age_current.png','after':[
 'The youngest high-burden cell contains six records and zero deaths. Its Wilson interval extends from 0% to 39.03%, demonstrating substantial uncertainty. The original notebook hid intervals for zero-death cells. Small race strata create similar limitations, and the race tables support description rather than causal interpretation.',
 'Actual mean medication counts for females versus males are 5.58 versus 3.59 in the lowest burden group, 8.08 versus 8.13 in the middle group, and 11.69 versus 11.38 in the highest group. The original bubble-size calculation used bin midpoints and discarded zero-medication records from that average. Correcting it shows that treatment histories should not simply be described as equal.',
 'In the restricted exploratory model, medication count has OR 1.036 (p = 0.048) and encounter count has OR 1.00458 per encounter (p < 0.001), while the male-versus-female OR remains 1.848. These histories may reflect illness near death and are not baseline exposure measures. Persistence of a coefficient does not rule out mediation or establish why the association exists.'
 ]},
 {'heading':'Exploratory diagnoses and interpretation','paragraphs':[
 'Encounter composition',
 'Across the restricted condition strata, acute-share comparisons have Holm-adjusted p-values of 1.000, 0.611 and 1.000. There is insufficient evidence of distributional differences under this comparison family. This is not evidence that access to care, care quality or care-seeking behaviour is equivalent. The full export contains 1,333 encounters classified as other, which are excluded from the acute/routine-share denominator but retained in total encounter counts.',
 'Diagnosis categories',
 'Keyword flags identify diabetes, chronic kidney disease, COPD, cancer-related descriptions, heart failure, stroke and hypertension. Among records with at least one flag, females have 70 deaths among 656 records (10.67%) and males have 126 among 703 (17.92%). These broad, overlapping categories do not measure severity, and keyword matching can misclassify suspected disease, history or benign neoplasms. Restriction to this subset cannot establish that severity or physiological reserve explains the sex association.',
 'Limitations',
 'Synthetic data inherit assumptions from their generator and cannot establish population estimates for Delaware. Uncertainty intervals and p-values describe variation under the statistical model, not uncertainty about simulator validity. The cohort selection process and generation seed are unknown. Historical condition and medication counts may depend on survival duration, while encounter counts can increase near death. These features preclude a clean temporal or causal interpretation.',
 'Age at reference is a birth-cohort covariate for deceased records. Replacing it with age at death would not create a valid baseline-age adjustment, because age at death is determined by the outcome process. A survival analysis would require explicit entry dates, baseline covariates, censoring rules and follow-up. The present models also assume a linear relationship between continuous predictors and log-odds, which is not fully established by grouped plots.',
 'The analysis includes multiple exploratory comparisons. Holm correction is applied to specified test families, not to every model coefficient in the project. No claim of clinical prediction is made: discrimination, calibration, external validation and clinical utility have not been evaluated. Real-world sex differences have complex and context-dependent explanations (Crimmins, Shim and Zhang, 2019), none of which is identified by this synthetic analysis.',
 'Conclusion',
 'Recorded sex and age at reference are associated with death status in this export. Condition-count findings depend on adjustment and cohort definition, while the interaction analysis gives insufficient evidence of modification on the log-odds scale. The corrected project demonstrates reproducible data preparation, statistical comparison and careful communication. Further work should define a longitudinal question, use code-based validated condition definitions and assess sensitivity to record duration before seeking causal or clinical interpretations.'
 ]},
 {'heading':'References and reproducibility','paragraphs':refs+[
 'Project files',
 'notebooks/assessment.ipynb contains the executed analysis. src/analysis.py contains shared validation and statistical functions. outputs/ contains rerun tables. data/manifest.json records hashes and the reference-date convention. scripts/run_notebooks.py and scripts/build_reports.py regenerate the analysis and these reports. tests/test_analysis.py checks the corrected boundary and statistical cases.',
 'The companion results_review.ipynb audits the original notebook\'s saved aggregate counts. Its historical age-band table is clearly distinguished from the fixed-date rerun. The repository does not include the assessment exemplars or publish the student identifier from the original essay.',
 'Generative AI disclosure',
 'The original assessment disclosed AI assistance with coding, statistical analysis and writing. This portfolio revision also used AI assistance to review inconsistencies, refactor code, improve statistical reporting and prepare documentation. The repository records executable methods, source provenance and limitations so that its claims can be independently checked. This revision should be reviewed and understood by the project author before being discussed in interviews.'
 ]},
]
NAVY=colors.HexColor('#183d60');GREY=colors.HexColor('#526577')
styles=getSampleStyleSheet()
styles.add(ParagraphStyle(name='BodyPortfolio',fontName='Helvetica',fontSize=10.4,leading=14.6,spaceAfter=9,textColor=colors.HexColor('#243440')))
styles.add(ParagraphStyle(name='HeadingPortfolio',fontName='Helvetica-Bold',fontSize=20,leading=25,spaceAfter=17,textColor=NAVY))
styles.add(ParagraphStyle(name='SubPortfolio',fontName='Helvetica-Bold',fontSize=12,leading=16,spaceBefore=7,spaceAfter=8,textColor=NAVY))
styles.add(ParagraphStyle(name='CellPortfolio',fontName='Helvetica',fontSize=8.7,leading=12))
def paragraph(text,style='BodyPortfolio'):return Paragraph(escape(text),styles[style])
def table_flow(data,width=475):
 sizes=[width/len(data[0])]*len(data[0])
 data=[[paragraph(str(v),'CellPortfolio') for v in rr] for rr in data]
 t=Table(data,colWidths=sizes,repeatRows=1,hAlign='LEFT')
 t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e7eff5')),('VALIGN',(0,0),(-1,-1),'TOP'),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7),('LINEBELOW',(0,0),(-1,0),.7,NAVY),('LINEBELOW',(0,1),(-1,-1),.25,colors.HexColor('#ccd7df'))]))
 return t

def footer(c,d):
 c.setFont('Helvetica',8);c.setFillColor(GREY);c.drawString(58,30,'Bhakti Doshi | Synthetic Delaware EHR analysis');c.drawRightString(537,30,str(d.page))
flow=[]; markdown=['# '+pages[0]['heading'],'']
for i,page in enumerate(pages):
 if i:flow.append(PageBreak());markdown.extend(['','## '+page['heading'],''])
 flow.append(paragraph(page['heading'],'HeadingPortfolio'))
 for txt in page.get('paragraphs',[]):
  flow.append(paragraph(txt,'SubPortfolio' if len(txt)<55 and i!=6 and not txt.startswith('Bhakti') else 'BodyPortfolio'));markdown.extend([txt,''])
 if page.get('image'):
  flow.append(Image(str(FIG/page['image']),width=475,height=243));flow.append(Spacer(1,10));markdown.extend([f'![Analysis figure](../figures/{page["image"]})',''])
 if page.get('table'):
  flow.append(table_flow(page['table']));flow.append(Spacer(1,10))
  markdown.append('| '+' | '.join(page['table'][0])+' |');markdown.append('| '+' | '.join(['---']*len(page['table'][0]))+' |')
  for rr in page['table'][1:]:markdown.append('| '+' | '.join(rr)+' |')
  markdown.append('')
 for txt in page.get('after',[]):flow.append(paragraph(txt));markdown.extend([txt,''])
SimpleDocTemplate(str(REP/'Essay.pdf'),pagesize=(595,842),rightMargin=58,leftMargin=58,topMargin=48,bottomMargin=48,title=pages[0]['heading'],author='Bhakti Doshi').build(flow,onFirstPage=footer,onLaterPages=footer)
(REP/'Essay.md').write_text('\n'.join(markdown)+'\n')
# PDF slide deck with matching clean white/blue styling and chart-led evidence.
slides=[
 ('Recorded condition burden and death status', ['Synthetic Delaware EHR analysis','Bhakti Doshi','Revised portfolio edition | 27 September 2026'],None),
 ('The Delaware synthetic dataset',['1,753 synthetic records, with 253 recorded deaths (14.43%).','Synthea provides simulated health histories, not a representative sample of current Delaware residents.','The generator version and seed were not supplied.'],None),
 ('Data and analysis workflow',['Patient, condition, medication and encounter CSVs linked by patient ID.','107,376 condition rows, 191,649 medication rows and 173,900 encounter rows.','Validated joins and dates, distinct historical counts, Wilson intervals and exploratory logistic models.'],None),
 ('Cohort and demographic definitions',['875 female and 878 male records.','Fixed reference date: 4 October 2024, the latest observed encounter start.','Age at reference is approximately 30-75 years. For deceased records it is hypothetical attained age, not age at death.'],None),
 ('Exclusions change the outcome distribution',['Restricting to 8-40 descriptions retains 1,716 records and 231 deaths.','37 excluded records contain 22 deaths: 2.11% of records but 8.70% of deaths.','Death proportion falls by 0.97 percentage points. The full export remains the primary descriptive cohort.'],None),
 ('Recorded burden and death proportion',['Corrected groups: 8-19, 20-29 and 30-40 descriptions.','Restricted-cohort proportions: 11.22%, 12.68% and 23.35%.'], 'burden_current.png'),
 ('Age at reference and death status',['All nonempty groups show Wilson 95% intervals.','The youngest high-burden cell has 0/6 deaths, with an upper interval limit of 39.03%.'], 'age_current.png'),
 ('Recorded sex and death status',['Male death proportions are higher within each restricted burden stratum.','Ratios: 1.81, 1.58 and 1.73. Corrected Holm p-values: 0.016, 0.037 and 0.037.'], 'sex_current.png'),
 ('Condition counts and adjustment',['Unadjusted condition OR: 1.019 in the full export and 1.039 in the restricted cohort.','Age/sex-adjusted condition OR: 0.967 in the full export (p = 0.002), compared with 0.983 (p = 0.159) in the restricted cohort.','Cohort definition and adjustment change the conclusion. Inverse coefficients do not demonstrate protection.'],None),
 ('Sex-by-burden interaction',['Restricted cohort: interaction OR 0.996 (95% CI 0.951-1.042), p = 0.847.','Full export: interaction OR 1.004 (0.964-1.045), p = 0.855.','Insufficient evidence of modification on the log-odds scale. This does not prove equal effects.'],None),
 ('Medication history by recorded sex',['Mean counts use actual distinct medication descriptions.','The lowest-burden means differ: 5.58 for females and 3.59 for males. Historical counts do not measure concurrent treatment.'], 'medication_means.png'),
 ('Supported conclusions',['Male-versus-female adjusted OR is about 1.84 in both cohorts.','Condition-count associations depend on cohort definition and adjustment.','The analysis does not establish whether severity, behaviour or physiological reserve explains these patterns.'],None),
 ('Limits and further work',['Synthetic data, unknown generation settings and historical exposures limit interpretation.','There are 25 deaths before age 20 despite adult reference ages. These are different age concepts.','A longitudinal study needs entry dates, baseline conditions, follow-up and validated diagnosis definitions.'],None),
 ('References',['Walonoski et al. (2018), JAMIA, 25(3), 230-238. doi:10.1093/jamia/ocx079','Fortin et al. (2012), Annals of Family Medicine, 10(2), 142-151. doi:10.1370/afm.1337','Crimmins, Shim and Zhang (2019), Clinical Chemistry, 65(1), 135-145. doi:10.1373/clinchem.2018.288332','Synthea CSV File Data Dictionary. Full links and provenance are in the essay and repository.'],None),
 ('Appendix: methods and reproducibility',['Included compressed extracts retain all rows and only required columns.','Run both notebooks, eight targeted tests and the report builder using Python 3.12.','Source/extract hashes, fixed cutoff and model formulas are documented. No clinical prediction claim is made.'],None),
 ('Appendix: adjusted models',['Full export / restricted cohort, respectively:','Male versus female: OR 1.836 / 1.835.','Age at reference, per year: OR 1.083 / 1.082.','Condition count, per description: OR 0.967 / 0.983.','Full confidence intervals, sample sizes and p-values are in outputs/models.csv.'],None),
 ('Appendix: encounter composition',['Acute-share Mann-Whitney comparisons use one Holm family across three burden strata.','Adjusted p-values: 1.000, 0.611 and 1.000. Routine share is complementary and is not tested twice.','The full export has 1,333 other-class encounters, excluded from the share denominator but included in total encounter counts.'],None),
 ('Appendix: exploratory diagnosis flags',['Among records matching at least one broad diagnosis category: females 70/656 deaths (10.67%), males 126/703 (17.92%).','Keyword categories overlap and do not measure severity. Benign or historical diagnoses may match broad terms.','Sparse race and disease cells require denominators and uncertainty, not causal explanations.'],None),
 ('Appendix: medication history',['Full-export death proportions are 9.68%, 8.97%, 10.72%, 16.95% and 19.69% across medication groups.','The pattern is not strictly monotonic. Association does not show medication effects on mortality.'], 'medication_current.png'),
]
(REP/'presentation_source.json').write_text(json.dumps([{'title':t,'text':b,'figure':f} for t,b,f in slides],indent=2)+'\n')
W,H=960,540
c=canvas.Canvas(str(REP/'Presentation.pdf'),pagesize=(W,H));c.setTitle('Recorded condition burden and death status');c.setAuthor('Bhakti Doshi')
slide_title=ParagraphStyle('SlideTitle',fontName='Helvetica-Bold',fontSize=31,leading=36,textColor=NAVY)
slide_body=ParagraphStyle('SlideBody',fontName='Helvetica',fontSize=21,leading=29,textColor=colors.HexColor('#243440'))
slide_small=ParagraphStyle('SlideSmall',parent=slide_body,fontSize=17,leading=23)
for i,(title,body,figure) in enumerate(slides):
 p=Paragraph(escape(title),slide_title);_,h=p.wrap(W-100,100);p.drawOn(c,50,H-40-h)
 y=H-62-h
 if figure:
  # Figure below two concise text paragraphs, sized to preserve aspect ratio.
  for txt in body:
   p=Paragraph(escape(txt),slide_small);_,th=p.wrap(W-100,100);p.drawOn(c,50,y-th);y-=th+8
  iw,ih=ImageReader(str(FIG/figure)).getSize();height=min(300,y-50);width=height*iw/ih
  c.drawImage(str(FIG/figure),(W-width)/2,45,width=width,height=height,mask='auto')
 else:
  for txt in body:
   p=Paragraph(escape(txt),slide_body if i!=13 else slide_small);_,th=p.wrap(W-120,350)
   if y-th<55:raise ValueError(f'Slide {i+1} text overflow')
   p.drawOn(c,60,y-th);y-=th+22
 c.setFont('Helvetica',9);c.setFillColor(GREY)
 c.drawString(50,20,'Bhakti Doshi | Synthetic data | Fixed reference: 2024-10-04')
 c.drawRightString(W-50,20,f'{i+1:02d} / {len(slides)}')
 c.showPage()
c.save()
print('Created essay and 19-slide presentation.')
