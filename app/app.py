from __future__ import annotations
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
from skna_framework.io import discover_recordings, read_recording, read_table
from skna_framework.analysis import RAW_ECG,FILT_ECG,SKNA_CH,UAP_CANDS,first_existing,to_uv,event_row,threshold_row,phase_summary,sequential_replay,replay_metrics,downsample

st.set_page_config(page_title='SKNA Cohort Explorer', layout='wide', page_icon='🫀')
st.title('SKNA Cohort Explorer')
st.caption('Interactive per-recording exploration of recorded physiology preserved in the processed files, ECG-derived SKNA, adaptive thresholds, burst activity and sequential replay.')

@st.cache_data(show_spinner=False)
def cached_discover(source_strings):
    return discover_recordings(source_strings)
@st.cache_data(show_spinner='Loading selected recording…')
def cached_read(kind,source,member):
    return read_recording({'kind':kind,'source':Path(source),'member':member})
@st.cache_data(show_spinner=False)
def cached_table(path):
    return read_table(path)

def add_event(fig,onset,offset,row=None,col=None):
    kw={} if row is None else {'row':row,'col':col}
    fig.add_vrect(x0=onset,x1=offset,fillcolor='gold',opacity=.12,line_width=0,**kw)
    fig.add_vline(x=onset,line_dash='dash',line_color='black',line_width=1,**kw)
    fig.add_vline(x=offset,line_dash='dash',line_color='darkorange',line_width=1,**kw)

def line_fig(df,cols,title,ytitle,onset=None,offset=None,uv=False,max_points=25000):
    d=downsample(df[['time_s']+[c for c in cols if c in df.columns]].copy(),max_points)
    fig=go.Figure()
    for c in cols:
        if c in d:
            y=to_uv(d[c]) if uv else d[c]
            fig.add_trace(go.Scattergl(x=d.time_s,y=y,mode='lines',name=c,line={'width':1}))
    if onset is not None: add_event(fig,onset,offset)
    fig.update_layout(title=title,xaxis_title='Time [s]',yaxis_title=ytitle,height=430,legend={'orientation':'h'})
    return fig

with st.sidebar:
    st.header('Data source')
    default_data=str(ROOT/'examples'/'001_signals_ecg_skna.csv')
    source_text=st.text_area('Processed recording source(s)', value=default_data, help='One path per line. Each path can be a directory, a processed-signal ZIP, or a *_signals_ecg_skna.csv file.')
    events_path=st.text_input('INAP events CSV', value=str(ROOT/'examples'/'example_events.csv'))
    thresholds_path=st.text_input('Threshold summary CSV', value=str(ROOT/'examples'/'example_thresholds.csv'))
    st.caption('The bundled defaults are synthetic. For your cohort, enter full paths to processed CSV files, directories, or ZIP archives.')

sources=[x.strip() for x in source_text.splitlines() if x.strip()]
index=cached_discover(tuple(sources))
events=cached_table(events_path)
thresholds=cached_table(thresholds_path)

if not index:
    st.warning('No processed recordings were found. Put your cohort ZIP files in `data/processed/` or enter their paths in the sidebar.')
    st.code('data/processed/\n├── first.zip\n└── second.zip')
    st.stop()

with st.sidebar:
    st.header('Recording')
    pig=st.selectbox('Pig / recording', list(index.keys()))
    st.caption(f'{len(index)} recordings discovered')
    st.header('Replay settings')
    window_s=st.number_input('Trailing window [s]',5.,120.,30.,5.)
    hop_s=st.number_input('Update interval [s]',1.,60.,10.,1.)
    occ_thr=st.number_input('Activation occupancy [%]',0.,100.,5.,1.)
    persist=st.number_input('Persistence [consecutive windows]',1,10,2,1)

entry=index[pig]
df=cached_read(entry['kind'],str(entry['source']),entry['member'])
if 'time_s' not in df.columns:
    st.error('Selected signal file has no `time_s` column.'); st.stop()
ev=event_row(events,pig); th=threshold_row(thresholds,pig)
if ev is None:
    st.error(f'No event row found for Pig {pig}.'); st.stop()
onset=float(ev['t_start_s']); offset=float(ev['t_end_s'])
if th is None or 'selected_threshold_uV' not in th.index:
    st.error(f'No selected threshold found for Pig {pig}.'); st.stop()
threshold_uv=float(th['selected_threshold_uV'])
skna_col='skna_med' if 'skna_med' in df.columns else None
if skna_col is None:
    st.error('Selected recording has no `skna_med` column.'); st.stop()
skna_uv=to_uv(df[skna_col])

phase=phase_summary(df.time_s,skna_uv,threshold_uv,onset,offset)
# Sanity-check the mV -> µV conversion against the frozen baseline median.
if th is not None and 'baseline_median_uV' in th.index and pd.notna(th['baseline_median_uV']):
    observed_base=float(phase.loc[phase.phase=='Baseline','median_skna_uV'].iloc[0])
    expected_base=float(th['baseline_median_uV'])
    rel_err=abs(observed_base-expected_base)/max(abs(expected_base),1e-12)
    if rel_err > 0.05:
        st.warning(f'SKNA unit sanity check: baseline median from signal is {observed_base:.4g} µV but threshold table reports {expected_base:.4g} µV. Check that this processed file uses the expected mV storage convention.')
replay=sequential_replay(df.time_s,skna_uv,threshold_uv,window_s,hop_s,occ_thr,int(persist))
rm=replay_metrics(replay,onset,offset)

c1,c2,c3,c4,c5=st.columns(5)
c1.metric('Pig',str(pig)); c2.metric('INAP duration',f'{offset-onset:.1f} s'); c3.metric('Threshold',f'{threshold_uv:.3f} µV')
inapchg=float(phase.loc[phase.phase=='INAP','median_change_from_baseline_pct'].iloc[0]); c4.metric('Median SKNA change',f'{inapchg:+.1f}%')
c5.metric('Replay', 'Triggered' if rm['trigger_success'] else 'No trigger', f"{rm['latency_s']:.1f} s latency" if rm['trigger_success'] else None)

T=st.tabs(['Overview','Raw signals','Processed SKNA','Burst analysis','Sequential replay','Results & tables'])

with T[0]:
    st.subheader(f'Pig {pig}: event-centred overview')
    uap=first_existing(df,UAP_CANDS)
    cols=[c for c in [uap,'Heart Rate','SpO2','RA-MAP','BP'] if c]
    st.plotly_chart(line_fig(df,cols,'Physiological context','Recorded units',onset,offset),use_container_width=True)
    d=pd.DataFrame({'time_s':df.time_s,'Median SKNA [µV]':skna_uv})
    fig=line_fig(d,['Median SKNA [µV]'],'Median ECG-derived SKNA','SKNA [µV]',onset,offset)
    fig.add_hline(y=threshold_uv,line_dash='dot',line_color='crimson',annotation_text='Adaptive threshold')
    st.plotly_chart(fig,use_container_width=True)

with T[1]:
    st.subheader('Recorded / raw channels preserved in the processed file')
    st.info('This tab does not open a separate raw-data file. The supplied *_signals_ecg_skna.csv files already contain copies of the original recorded channels (ECG, UAP, SpO₂, haemodynamics, etc.) together with the processed ECG/SKNA columns. Values here are read directly from the selected processed CSV/ZIP member.')
    available=[c for c in df.columns if c!='time_s' and not c.startswith('compact_skna') and not c.startswith('ecg_filt__') and c!='skna_med']
    default=[c for c in RAW_ECG+[first_existing(df,UAP_CANDS),'SpO2','Heart Rate','RA-MAP'] if c in available]
    sel=st.multiselect('Signals to display',available,default=default)
    if sel:
        # one vertically stacked axis per selected signal for legibility
        d=downsample(df[['time_s']+sel],25000)
        fig=make_subplots(rows=len(sel),cols=1,shared_xaxes=True,vertical_spacing=.015,subplot_titles=sel)
        for i,c in enumerate(sel,1):
            fig.add_trace(go.Scattergl(x=d.time_s,y=d[c],mode='lines',name=c,line={'width':.8},showlegend=False),row=i,col=1)
            add_event(fig,onset,offset,row=i,col=1)
        fig.update_xaxes(title_text='Time [s]',row=len(sel),col=1); fig.update_layout(height=max(500,190*len(sel)),title='Recorded channels contained in processed file')
        st.plotly_chart(fig,use_container_width=True)
    with st.expander('Available columns'):
        st.write(list(df.columns))

with T[2]:
    st.subheader('Processed ECG and SKNA')
    proc_tabs=st.tabs(['Filtered ECG','Channel SKNA envelopes','Median SKNA'])
    with proc_tabs[0]:
        have=[c for c in FILT_ECG if c in df]
        st.plotly_chart(line_fig(df,have,'500-Hz high-pass filtered ECG','Amplitude [recorded units]',onset,offset),use_container_width=True)
    with proc_tabs[1]:
        have=[c for c in SKNA_CH if c in df]
        st.plotly_chart(line_fig(df,have,'Channel-specific SKNA envelopes','SKNA [µV]',onset,offset,uv=True),use_container_width=True)
    with proc_tabs[2]:
        tmp=pd.DataFrame({'time_s':df.time_s,'Median SKNA':skna_uv})
        fig=line_fig(tmp,['Median SKNA'],'Median SKNA used for analysis','SKNA [µV]',onset,offset)
        fig.add_hline(y=threshold_uv,line_dash='dot',line_color='crimson',annotation_text=f'{threshold_uv:.3f} µV')
        st.plotly_chart(fig,use_container_width=True)
        st.dataframe(phase,use_container_width=True,hide_index=True)

with T[3]:
    st.subheader('Adaptive threshold and burst activity')
    tmp=pd.DataFrame({'time_s':df.time_s,'Median SKNA':skna_uv})
    d=downsample(tmp,30000)
    fig=go.Figure()
    fig.add_trace(go.Scattergl(x=d.time_s,y=d['Median SKNA'],mode='lines',name='Median SKNA',line={'width':1}))
    burst=d['Median SKNA'].to_numpy()>threshold_uv
    fig.add_trace(go.Scattergl(x=d.time_s[burst],y=d['Median SKNA'][burst],mode='markers',name='Burst-active samples',marker={'size':3}))
    fig.add_hline(y=threshold_uv,line_dash='dash',line_color='crimson',annotation_text='Selected threshold')
    add_event(fig,onset,offset); fig.update_layout(height=480,xaxis_title='Time [s]',yaxis_title='SKNA [µV]')
    st.plotly_chart(fig,use_container_width=True)
    if th is not None:
        show=[c for c in ['baseline_median_uV','baseline_mad_uV','gmm_threshold_uV','q95_threshold_uV','mad6_threshold_uV','selected_threshold_uV','selected_source','combined_threshold_baseline_occupancy_pct','combined_threshold_inap_occupancy_pct'] if c in th.index]
        st.dataframe(pd.DataFrame({'metric':show,'value':[th[c] for c in show]}),use_container_width=True,hide_index=True)
    st.markdown('**Phase-level burst occupancy**')
    st.bar_chart(phase.set_index('phase')['burst_occupancy_pct'])

with T[4]:
    st.subheader('Sequential replay under real-time information constraints')
    st.caption('Each replay decision uses only samples available up to the current window end. Burst occupancy is the percentage of median-SKNA samples above the recording-specific threshold within the preceding window. This is sequential processing, not statistical causal inference.')
    fig=make_subplots(rows=2,cols=1,shared_xaxes=True,vertical_spacing=.08,subplot_titles=['Trailing-window burst occupancy','Trigger state'])
    fig.add_trace(go.Scatter(x=replay.window_end_s,y=replay.burst_occupancy_pct,mode='lines+markers',name='Burst occupancy'),row=1,col=1)
    fig.add_hline(y=occ_thr,line_dash='dash',line_color='crimson',row=1,col=1)
    fig.add_trace(go.Scatter(x=replay.window_end_s,y=replay.trigger_on.astype(int),mode='lines',line_shape='hv',name='Trigger'),row=2,col=1)
    add_event(fig,onset,offset,row=1,col=1); add_event(fig,onset,offset,row=2,col=1)
    fig.update_yaxes(title_text='Occupancy [%]',row=1,col=1); fig.update_yaxes(title_text='State',tickvals=[0,1],row=2,col=1); fig.update_xaxes(title_text='Time [s]',row=2,col=1)
    fig.update_layout(height=600)
    st.plotly_chart(fig,use_container_width=True)
    a,b,c,d=st.columns(4); a.metric('Window',f'{window_s:g} s'); b.metric('Update',f'{hop_s:g} s'); c.metric('Persistence',f'{int(persist)} windows'); d.metric('Detection latency',f"{rm['latency_s']:.1f} s" if rm['trigger_success'] else 'Not detected')
    st.dataframe(replay,use_container_width=True,hide_index=True)

with T[5]:
    st.subheader('Recording results and data tables')
    st.markdown('**Event timing**'); st.dataframe(pd.DataFrame([ev]),use_container_width=True,hide_index=True)
    st.markdown('**Phase summary**'); st.dataframe(phase,use_container_width=True,hide_index=True)
    if th is not None:
        st.markdown('**Threshold summary**'); st.dataframe(pd.DataFrame([th]),use_container_width=True,hide_index=True)
    st.markdown('**Selected recording data preview**')
    st.dataframe(df.head(1000),use_container_width=True)
    export=phase.copy(); export.insert(0,'pig_id',pig)
    st.download_button('Download phase summary CSV',export.to_csv(index=False).encode(),'pig_%s_phase_summary.csv'%pig,'text/csv')
    st.download_button('Download replay CSV',replay.to_csv(index=False).encode(),'pig_%s_replay.csv'%pig,'text/csv')
