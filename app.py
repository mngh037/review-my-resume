import streamlit as st
import openai
import os
from openai import OpenAI
import pdfplumber
import docx2txt
import matplotlib.pyplot as plt
import numpy as np
from dotenv import load_dotenv
from bs4 import BeautifulSoup

load_dotenv()
MODEL = "gpt-4o"
TEMPERATURE = 1.0

# Load OpenAI API Key in .env file
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def extract_text_from_pdf(pdf_file):
    with pdfplumber.open(pdf_file) as pdf:
        text = "\n".join([page.extract_text() for page in pdf.pages if page.extract_text()])
    return text

def extract_text_from_docx(docx_file):
    text = docx2txt.process(docx_file)
    return text

def get_match_score(resume, job_description):
    prompt = f"""
    Resume:
    {resume}
    
    Job Description:
    {job_description}
    """
    
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "system", "content": "You are an expert career coach assessing resume matches."},
                  {"role": "user", "content": prompt}]
    )
    
    return response.choices[0].message.content

st.title("📄 Resume Match")
st.write("Upload your resume and job description PDF to check the match score and get suggestions!")

uploaded_resume = st.file_uploader("Upload Resume (PDF)", type=["pdf", "docx"])
resume_text = ""
if uploaded_resume is not None:
    if uploaded_resume.name.endswith(".pdf"):
        resume_text = extract_text_from_pdf(uploaded_resume)
    elif uploaded_resume.name.endswith(".docx"):
        resume_text = extract_text_from_docx(uploaded_resume)
    st.success("Resume uploaded and processed!")
else:
    resume_text = st.text_area("Or paste your Resume:")

uploaded_jd = st.file_uploader("Upload Job Description (PDF)", type=["pdf"])
job_desc_text = ""
if uploaded_jd is not None:
    if uploaded_jd.name.endswith(".pdf"):
        jd_text = extract_text_from_pdf(uploaded_jd)
    elif uploaded_jd.name.endswith(".docx"):
        jd_text = extract_text_from_docx(uploaded_jd)
    st.success("Job description uploaded and processed!")
else:
    jd_text = st.text_area("Or paste Job Description:")

if st.button("Check Match"): 
    if resume_text and jd_text:
        result = get_match_score(resume_text, jd_text)
        st.subheader("Match Analysis")
        st.write(result)
        
        # Extract score breakdown from the response
        score_breakdown_section = result.split("- Score Breakdown:")[1].split("- Strengths:")[0] if "- Score Breakdown:" in result else ""
        breakdown_lines = [s.strip() for s in score_breakdown_section.split("\n") if s and ":" in s]
        breakdown = {line.split(":")[0]: int(line.split(":")[1].replace("%", "")) for line in breakdown_lines}

    else:
        st.warning("Please provide both resume and job description!")
