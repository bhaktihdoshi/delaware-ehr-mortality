import unittest
from pathlib import Path
import tempfile
import numpy as np
import pandas as pd
from src.analysis import condition_bins,holm_adjust,wilson_ci,compare_sexes,load_tables,prepare_cohort

class AnalysisTests(unittest.TestCase):
    def test_condition_boundaries(self):
        actual=condition_bins(pd.Series([7,8,19,20,29,30,40,41]))
        self.assertTrue(pd.isna(actual.iloc[0]) and pd.isna(actual.iloc[-1]))
        self.assertEqual(actual.iloc[1:-1].astype(str).tolist(),['8-19','8-19','20-29','20-29','30-40','30-40'])
    def test_holm_monotonicity_regression(self):
        np.testing.assert_allclose(holm_adjust([.018698,.031596,.005369]),[.037396,.037396,.016107])
        np.testing.assert_allclose(holm_adjust([.04,.01,.03]),[.06,.03,.06])
    def test_zero_death_interval(self):
        lo,hi=wilson_ci(0,4)
        self.assertAlmostEqual(lo,0);self.assertAlmostEqual(hi,.48989083645)
        self.assertTrue(np.isnan(wilson_ci(0,0)[0]))
    def test_absent_group(self):
        self.assertTrue(np.isnan(compare_sexes(0,0,10,2)['ratio']))
    def test_saved_sex_ratio(self):
        self.assertAlmostEqual(compare_sexes(374,30,366,53)['ratio'],1.80528233151184)
    def test_missing_files_explained(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(FileNotFoundError,'patients'):
                load_tables(directory)
    def test_dates_counts_and_no_encounter_denominator(self):
        tables={
          'patients':pd.DataFrame({'Id':['a','b'],'BIRTHDATE':['1980-01-01','1985-01-01'],'DEATHDATE':['2020-01-01',''],'GENDER':['F','M'],'RACE':['white','black']}),
          'conditions':pd.DataFrame({'PATIENT':['a','a','b'],'DESCRIPTION':['diabetes','diabetes','future'],'START':['2010-01-01','2011-01-01','2030-01-01']}),
          'medications':pd.DataFrame({'PATIENT':['a'],'DESCRIPTION':['medicine'],'START':['2010-01-01']}),
          'encounters':pd.DataFrame({'PATIENT':['a','a','b'],'ENCOUNTERCLASS':['emergency','wellness','home'],'START':['2010-01-01','2011-01-01','2012-01-01']})}
        df=prepare_cohort(tables,'2024-10-04').set_index('Id')
        self.assertEqual(df.loc['a','Num_Conditions'],1)
        self.assertEqual(df.loc['b','Num_Conditions'],0)
        self.assertEqual(df.loc['a','Acute_share'],50)
        self.assertTrue(pd.isna(df.loc['b','Acute_share']))
        self.assertGreater(df.loc['a','Age'],df.loc['a','Age_at_death'])
        self.assertEqual(df.Deceased.sum(),1)
    def test_published_extract_counts(self):
        tables=load_tables(Path(__file__).resolve().parents[1]/'data'/'raw')
        self.assertEqual(len(tables['patients']),1753)
        df=prepare_cohort(tables,'2024-10-04')
        self.assertEqual(df.Deceased.sum(),253)
        restricted=df[df.Num_Conditions.between(8,40)]
        self.assertEqual((len(restricted),int(restricted.Deceased.sum())),(1716,231))

if __name__=='__main__':unittest.main()
