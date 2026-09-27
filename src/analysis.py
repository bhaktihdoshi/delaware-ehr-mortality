"""Descriptive Synthea EHR analysis. No prospective or causal interpretation."""
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.multitest import multipletests
from statsmodels.stats.proportion import proportion_confint
import statsmodels.formula.api as smf

CONDITION_LABELS = ['8-19', '20-29', '30-40']
REQUIRED = {
 'patients': {'Id','BIRTHDATE','DEATHDATE','GENDER','RACE'},
 'conditions': {'PATIENT','DESCRIPTION','START'},
 'medications': {'PATIENT','DESCRIPTION','START'},
 'encounters': {'PATIENT','ENCOUNTERCLASS','START'},
}
MAJOR_RULES = {
 'Diabetes': r'diabetes', 'CKD': r'chronic kidney|\bckd\b|renal failure|kidney disease',
 'COPD': r'\bcopd\b|chronic obstructive|emphysema',
 'Cancer': r'cancer|carcinoma|malignant|tumor|neoplasm',
 'Heart failure': r'congestive heart failure|heart failure|\bchf\b',
 'Stroke': r'stroke|cerebrovascular', 'Hypertension': r'hypertension|high blood pressure',
}

def condition_bins(values):
    """Retain original numeric boundaries and correct misleading labels."""
    return pd.cut(values, [8,20,30,41], labels=CONDITION_LABELS, right=False)

def holm_adjust(pvalues):
    values = np.asarray(pvalues, dtype=float)
    out = np.full(values.shape, np.nan)
    valid = np.isfinite(values)
    if valid.any():
        out[valid] = multipletests(values[valid], method='holm')[1]
    return out

def wilson_ci(deaths, n):
    if n == 0:
        return np.nan, np.nan
    if not 0 <= deaths <= n:
        raise ValueError('Deaths must be between zero and n.')
    return proportion_confint(deaths, n, method='wilson')

def compare_sexes(female_n, female_deaths, male_n, male_deaths):
    """Death-proportion ratio, Katz CI and a contingency test."""
    if min(female_n, male_n) <= 0:
        return dict(ratio=np.nan, ci_low=np.nan, ci_high=np.nan,
                    p_value=np.nan, test='Not estimable: absent group')
    if not (0 <= female_deaths <= female_n and 0 <= male_deaths <= male_n):
        raise ValueError('Invalid death count.')
    a,b,c,d = map(float, [male_deaths,male_n-male_deaths,female_deaths,female_n-female_deaths])
    table = np.array([[c,d],[a,b]])
    if (table.sum(axis=0) == 0).any():
        return dict(ratio=np.nan,ci_low=np.nan,ci_high=np.nan,p_value=1.,test='Fisher exact; no outcome variation')
    _,p,_,expected = stats.chi2_contingency(table, correction=False)
    test = 'Pearson chi-square'
    if (expected < 5).any():
        _,p = stats.fisher_exact(table)
        test = 'Fisher exact'
    corrected = min(a,b,c,d) == 0
    if corrected:
        a,b,c,d = a+.5,b+.5,c+.5,d+.5
    ratio = (a/(a+b))/(c/(c+d))
    se = np.sqrt(1/a-1/(a+b)+1/c-1/(c+d))
    lo,hi = np.exp(np.log(ratio)+np.array([-1,1])*stats.norm.ppf(.975)*se)
    return dict(ratio=ratio,ci_low=lo,ci_high=hi,p_value=p,test=test,
                continuity_correction=corrected)

def load_tables(data_dir):
    directory = Path(data_dir)
    paths = {name: next((directory/(name+ext) for ext in ('.csv.gz', '.csv') if (directory/(name+ext)).is_file()), None) for name in REQUIRED}
    absent = [name+'.csv[.gz]' for name,path in paths.items() if path is None]
    if absent:
        raise FileNotFoundError(f'Missing files in {directory}: {", ".join(absent)}. See data/README.md.')
    tables = {}
    for name, required in REQUIRED.items():
        table = pd.read_csv(paths[name], dtype=str)
        missing = required - set(table.columns)
        if missing:
            raise ValueError(f'{name}.csv missing columns: {sorted(missing)}')
        tables[name] = table
    patients = tables['patients']
    if patients.Id.isna().any() or patients.Id.duplicated().any():
        raise ValueError('patients.Id must be present and unique.')
    for name in ('conditions','medications','encounters'):
        table = tables[name]
        if table.PATIENT.isna().any() or not table.PATIENT.isin(patients.Id).all():
            raise ValueError(f'{name}: missing or unknown patient identifiers.')
    return tables

def prepare_cohort(tables, reference_date):
    """Use a supplied export cutoff; keep age at reference distinct from age at death.

    Age is hypothetical attained age at the cutoff for deceased records, preserving
    the original birth-cohort covariate. Neither age is a pre-outcome baseline age.
    Models are retrospective associations only.
    """
    cutoff = pd.Timestamp(reference_date)
    if pd.isna(cutoff):
        raise ValueError('A confirmed dataset reference date is required.')
    cutoff = cutoff.normalize()
    p = tables['patients'].copy()
    birth = pd.to_datetime(p.BIRTHDATE, errors='raise')
    death = pd.to_datetime(p.DEATHDATE.replace('', np.nan), errors='raise')
    if birth.isna().any() or (birth > cutoff).any() or (death < birth).any():
        raise ValueError('Missing or inconsistent birth/death dates.')
    p['Deceased'] = (death.notna() & (death <= cutoff)).astype(int)
    p['Age'] = (cutoff-birth).dt.days/365.25
    p['Age_at_death'] = ((death-birth).dt.days/365.25).where(p.Deceased.eq(1))
    p['Age_Group'] = pd.cut(p.Age,[20,40,60,80],right=False,labels=['20-39','40-59','60-79'])
    p['Gender'] = p.GENDER.map({'F':'Female','M':'Male'})
    if p.Gender.isna().any():
        raise ValueError('Unexpected or missing GENDER. Review categories before analysis.')
    cleaned = {}
    for name in ('conditions','medications','encounters'):
        t = tables[name].copy()
        start = pd.to_datetime(t.START, errors='raise', utc=True).dt.tz_localize(None)
        if start.isna().any():
            raise ValueError(f'{name}: missing START dates.')
        # Date-level cutoff includes the entire final day.
        t = t.loc[start < cutoff+pd.Timedelta(days=1)].copy()
        cleaned[name] = t
        if name == 'encounters':
            counts = t.groupby('PATIENT').size()
            column = 'Num_Encounters'
        else:
            if t.DESCRIPTION.isna().any():
                raise ValueError(f'{name}: missing DESCRIPTION affects distinct counts.')
            counts = t.groupby('PATIENT').DESCRIPTION.nunique()
            column = 'Num_Conditions' if name == 'conditions' else 'Num_Medications'
        p[column] = p.Id.map(counts).fillna(0).astype(int)
    p['Cond_Bin'] = condition_bins(p.Num_Conditions)
    p['Med_Bin'] = pd.cut(p.Num_Medications,[-1,0,2,5,10,np.inf],labels=['0','1-2','3-5','6-10','11+'])
    enc = cleaned['encounters']
    cls = enc.ENCOUNTERCLASS.str.lower().str.strip()
    enc['CareType'] = np.select([cls.isin(['emergency','inpatient','urgentcare','urgent care']),
                                cls.isin(['ambulatory','outpatient','wellness'])],
                               ['Acute','Routine'],default='Other')
    care = pd.crosstab(enc.PATIENT,enc.CareType).reindex(columns=['Acute','Routine','Other'],fill_value=0)
    p = p.join(care,on='Id')
    p[['Acute','Routine','Other']] = p[['Acute','Routine','Other']].fillna(0)
    denominator = (p.Acute+p.Routine).replace(0,np.nan)
    p['Acute_share'] = 100*p.Acute/denominator
    p['Routine_share'] = 100*p.Routine/denominator
    for label,pattern in MAJOR_RULES.items():
        t = cleaned['conditions']
        ids = t.loc[t.DESCRIPTION.str.contains(pattern,case=False,na=False,regex=True),'PATIENT']
        p['Has_'+label] = p.Id.isin(ids)
    return p

def summarise(frame, by):
    table = frame.groupby(by,observed=True).Deceased.agg(n='size',deaths='sum').reset_index()
    table['death_pct'] = 100*table.deaths/table.n
    ci = [wilson_ci(d,n) for d,n in zip(table.deaths,table.n)]
    table['ci_low_pct'] = [100*x[0] for x in ci]
    table['ci_high_pct'] = [100*x[1] for x in ci]
    return table

def model_table(frame, formula):
    result = smf.logit(formula,data=frame,missing='raise').fit(disp=False)
    if not result.mle_retvals.get('converged',False):
        raise RuntimeError('Logistic regression did not converge.')
    ci = result.conf_int()
    return pd.DataFrame({'term':result.params.index,'OR':np.exp(result.params),
                         'ci_low':np.exp(ci[0]),'ci_high':np.exp(ci[1]),'p_value':result.pvalues,
                         'n':int(result.nobs)}).reset_index(drop=True)
