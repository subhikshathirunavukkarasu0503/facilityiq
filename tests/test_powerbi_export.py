from pathlib import Path
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]

def test_powerbi_exports_exist_and_are_populated():
    expected={
      'equipment_health.csv':(9,{'device_id','domain','failure_probability','status'}),
      'energy_consumption.csv':(1000,{'date','hour','zone','power_kw_mean','power_kw_peak'}),
      'space_utilization.csv':(1000,{'date','hour','zone','occupancy_mean','desk_utilization_pct'}),
    }
    for name,(minimum,columns) in expected.items():
        df=pd.read_csv(ROOT/'data'/'powerbi'/name)
        assert len(df)>=minimum
        assert columns<=set(df.columns)
        assert not df[list(columns)].isnull().any().any()

def test_powerbi_measures_are_in_sane_ranges():
    e=pd.read_csv(ROOT/'data'/'powerbi'/'energy_consumption.csv')
    s=pd.read_csv(ROOT/'data'/'powerbi'/'space_utilization.csv')
    assert (e.power_kw_mean>=0).all()
    assert e.power_factor_mean.between(0,1).all()
    assert s.desk_utilization_pct.between(0,100).all()
    assert s.booking_rate.between(0,1).all()
