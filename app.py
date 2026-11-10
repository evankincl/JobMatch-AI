import os, hmac, json
import streamlit as st
from openai import OpenAI
from core import discover, save_jobs, list_jobs, update_status, extract_resume, match_job, tailor_resume, make_docx, supabase_credentials

st.set_page_config(page_title='JobMatch AI', page_icon='💼', layout='wide')
st.title('💼 JobMatch AI')
st.caption('Personal job discovery · Seattle metro + Remote US · $130k+ · Review before applying')

def secret(name, default=''):
    try: return st.secrets.get(name, os.getenv(name,default))
    except Exception: return os.getenv(name,default)

password=secret('APP_PASSWORD')
if not password:
    st.error('Set APP_PASSWORD in Streamlit secrets before using this app.')
    st.stop()
if not st.session_state.get('authenticated'):
    with st.form('login'):
        supplied=st.text_input('App password',type='password')
        submitted=st.form_submit_button('Sign in')
    if submitted and hmac.compare_digest(supplied,password):
        st.session_state.authenticated=True
        st.rerun()
    if submitted: st.error('Incorrect password')
    st.stop()

if not all(supabase_credentials({'SUPABASE_URL':secret('SUPABASE_URL'), 'SUPABASE_SERVICE_ROLE_KEY':secret('SUPABASE_SERVICE_ROLE_KEY')})):
    st.error('Configure SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in Streamlit secrets, then run schema.sql in Supabase SQL Editor.')
    st.stop()

secrets={'SUPABASE_URL':secret('SUPABASE_URL'),'SUPABASE_SERVICE_ROLE_KEY':secret('SUPABASE_SERVICE_ROLE_KEY')}
model=secret('OPENAI_MODEL','gpt-4.1-mini')
api_key=secret('OPENAI_API_KEY')
client=OpenAI(api_key=api_key) if api_key else None

with st.sidebar:
    st.subheader('Search settings')
    st.write('**Roles:** Operations Manager, Director of Operations, Strategy & Operations, Business Transformation')
    st.write('**Locations:** Seattle metro + Remote US')
    st.write('**Minimum salary:** $130,000 (unknown salaries included)')
    st.write('**Cadence:** Daily via GitHub Actions')
    st.info('Job sources are selected company Greenhouse/Lever boards. Edit config.json to expand coverage.')
    if st.button('Sign out'):
        for k in ('authenticated','resume_text','resume_filename','tailored','matches'): st.session_state.pop(k,None)
        st.rerun()

upload=st.file_uploader('Upload your master resume (PDF, DOCX or TXT)',type=['pdf','docx','txt'])
if upload is not None:
    try:
        resume=extract_resume(upload.name,upload.getvalue())
        if len(resume)<100: st.warning('Very little text extracted. Scanned PDFs need OCR or a text-based version.')
        if st.session_state.get('resume_filename')!=upload.name or st.session_state.get('resume_hash')!=hash(upload.getvalue()):
            st.session_state.resume_text=resume
            st.session_state.resume_filename=upload.name
            st.session_state.resume_hash=hash(upload.getvalue())
            st.session_state.pop('tailored',None)
        st.success(f'Resume loaded: {len(resume):,} characters. Stored only in this app session.')
    except Exception as e: st.error(f'Resume could not be read: {e}')

c1,c2=st.columns([1,3])
with c1:
    if st.button('🔎 Scan jobs now',type='primary'):
        with st.spinner('Checking company job boards...'):
            jobs,errors=discover()
            try:
                saved=save_jobs(jobs,secrets)
                st.success(f'Saved {saved} matching postings.')
            except Exception as e: st.error(f'Database error: {e}')
            if errors: st.warning('Some feeds failed: '+' | '.join(errors[:8]))

try: jobs=list_jobs(secrets)
except Exception as e:
    st.error(f'Unable to load jobs: {e}')
    st.stop()

st.metric('Jobs in database',len(jobs))
statuses=['new','review','approved','applied','skipped']
status_filter=st.multiselect('Statuses',statuses,default=['new','review','approved'])
visible=[j for j in jobs if j.get('status') in status_filter]
if not visible: st.info('No jobs to display. Scan now or wait for the scheduled scan.')

for job in visible:
    with st.expander(f"{job['title']} · {job['company']} · {job.get('location') or 'Location not specified'} [{job.get('status','new')}]"):
        sal=job.get('salary_min'),job.get('salary_max')
        st.write('**Salary:** '+(f"${float(sal[0]):,.0f}–${float(sal[1]):,.0f}" if all(v is not None for v in sal) else 'Not verified / not disclosed'))
        st.write(f"**Source:** {job.get('source','')} | **Posting:** {job['url']}")
        st.write((job.get('description') or 'No description supplied')[:4500])
        if client and st.session_state.get('resume_text'):
            if st.button('Evaluate fit',key='fit'+job['job_id']):
                try:
                    with st.spinner('Evaluating...'):
                        result=match_job(client,model,st.session_state.resume_text,job)
                        st.session_state.setdefault('matches',{})[job['job_id']]=result
                except Exception as e: st.error(f'AI matching failed: {e}')
            result=st.session_state.get('matches',{}).get(job['job_id'])
            if result:
                st.metric('Heuristic match score',f"{result.get('score','?')}/100")
                st.write(result.get('summary',''))
                st.write('**Evidence:**',result.get('matching_evidence',[]))
                st.write('**Gaps:**',result.get('gaps',[]))
            if st.button('Generate tailored resume',key='tailor'+job['job_id']):
                try:
                    with st.spinner('Tailoring resume...'):
                        tailored=tailor_resume(client,model,st.session_state.resume_text,job)
                        st.session_state.setdefault('tailored',{})[job['job_id']]=tailored
                except Exception as e: st.error(f'Resume generation failed: {e}')
            tailored=st.session_state.get('tailored',{}).get(job['job_id'])
            if tailored:
                st.write('**Draft preview — verify against your original resume before use**')
                st.json(tailored)
                st.warning('AI-generated resume is a draft. Verify dates, contact details, chronology, and every claim before submitting.')
                docbytes=make_docx(tailored,st.session_state.resume_text)
                st.download_button('Download tailored DOCX',docbytes,file_name='tailored_resume.docx',
                                   mime='application/vnd.openxmlformats-officedocument.wordprocessingml.document',key='download'+job['job_id'])
        else:
            st.caption('Upload a resume and configure OPENAI_API_KEY to enable personalized matching and tailoring.')
        st.write('**Review workflow**')
        new_status=st.selectbox('Status',statuses,index=statuses.index(job.get('status','new')),key='status'+job['job_id'])
        if st.button('Save status',key='save'+job['job_id']):
            try:
                update_status(job['job_id'],new_status,secrets)
                st.success('Status updated')
                st.rerun()
            except Exception as e: st.error(f'Update failed: {e}')
        if job.get('status') in ('approved','applied'):
            st.link_button('Open official application page',job['url'])
        else:
            st.caption('Mark as approved to reveal the application link. The app never auto-submits.')
