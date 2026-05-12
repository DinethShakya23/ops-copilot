# pages/3_Ingestion_Log.py

import streamlit as st
import json
import os
from datetime import datetime
from pathlib import Path

st.set_page_config(
    page_title='Ingestion Log', 
    page_icon='📥', 
    layout='wide'
)

st.title('📥 Ingestion Log')
st.caption('Document ingestion status and history')

STATE_FILE = 'ingestion_state.json'

# ── Load state ────────────────────────────────────────────
if not os.path.exists(STATE_FILE):
    st.info('No ingestion has run yet.')
    st.code('python ingest.py', language='bash')
    st.stop()

with open(STATE_FILE) as f:
    state = json.load(f)

# ── Show summary ──────────────────────────────────────────
last_run = datetime.fromisoformat(state['last_run'])

col1, col2 = st.columns(2)
col1.metric('Last ingestion', last_run.strftime('%Y-%m-%d %H:%M'))
col2.metric('Total files tracked', state['total_files'])

# ── Show file list ────────────────────────────────────────
st.divider()
st.subheader('Tracked Files')

import pandas as pd

files_data = []
for filepath, hash_val in state['files'].items():
    p = Path(filepath)
    files_data.append({
        'File': p.name,
        'Path': str(p.parent),
        'Hash (first 8)': hash_val[:8],
        'Exists': '✅' if p.exists() else '❌'
    })

df = pd.DataFrame(files_data)
st.dataframe(df, use_container_width=True)

# ── Manual re-ingestion ───────────────────────────────────
st.divider()
st.subheader('Manual Actions')

col_a, col_b = st.columns(2)

with col_a:
    if st.button('🔄 Re-ingest all files', type='primary'):
        with st.spinner('Ingesting...'):
            import subprocess
            result = subprocess.run(
                ['python', 'ingest.py'],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                st.success('✅ Ingestion complete! Refresh page.')
            else:
                st.error(f'Error: {result.stderr}')

with col_b:
    if st.button('🗑️ Clear database and re-ingest', type='secondary'):
        with st.spinner('Clearing and re-ingesting...'):
            import subprocess
            result = subprocess.run(
                ['python', 'ingest.py', '--clear'],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                st.success('✅ Database cleared and re-ingested!')
            else:
                st.error(f'Error: {result.stderr}')