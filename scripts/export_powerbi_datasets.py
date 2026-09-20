"""Export three clean analytics datasets for the FacilityIQ Power BI reports."""
from __future__ import annotations
from pathlib import Path
import pandas as pd
from facilityiq.ml.features import load_domain
from facilityiq.ml.predict import fleet_assessment

OUT=Path('data/powerbi'); OUT.mkdir(parents=True,exist_ok=True)
assessment=fleet_assessment()
assets=pd.DataFrame(assessment['hvac']+assessment['energy'])
assets.drop(columns=['anomalies'],errors='ignore').to_csv(OUT/'equipment_health.csv',index=False)

energy=load_domain('energy')
energy['date']=energy.timestamp.dt.date.astype(str)
energy['hour']=energy.timestamp.dt.hour
energy.groupby(['date','hour','zone','device_id'],as_index=False).agg(
 power_kw_mean=('power_kw','mean'),power_kw_peak=('power_kw','max'),
 voltage_v_mean=('voltage_v','mean'),power_factor_mean=('power_factor','mean'),
 thd_pct_mean=('thd_pct','mean')).to_csv(OUT/'energy_consumption.csv',index=False)

occ=load_domain('occupancy')
occ['date']=occ.timestamp.dt.date.astype(str); occ['hour']=occ.timestamp.dt.hour
occ['desk_utilization_pct']=100*occ.desk_occupied/occ.desk_total
occ['ghost_booking']=((occ.room_booked>0)&(occ.room_occupied==0)).astype(int)
occ.groupby(['date','hour','zone','device_id'],as_index=False).agg(
 occupancy_mean=('occupancy_count','mean'),occupancy_peak=('occupancy_count','max'),
 desk_utilization_pct=('desk_utilization_pct','mean'),
 booking_rate=('room_booked','mean'),ghost_bookings=('ghost_booking','sum')).to_csv(OUT/'space_utilization.csv',index=False)

print('Power BI datasets exported')
for p in sorted(OUT.glob('*.csv')):
 df=pd.read_csv(p); print(f'{p}: {len(df):,} rows x {len(df.columns)} columns')
