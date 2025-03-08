from pluggy import Result
import streamlit as st
import openai
import os
from openai import OpenAI
import pdfplumber
import docx2txt
import matplotlib.pyplot as plt
import numpy as np
from dotenv import load_dotenv
from annotated_text import annotated_text
import json

load_dotenv()
MODEL = "gpt-4o"
TEMPERATURE = 1.0

# Load OpenAI API Key in .env file
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Load the prompt prepared for resume review
with open("./prompt.txt", "r") as f:
    template = f.read()

def extract_text_from_pdf(pdf_file):
    with pdfplumber.open(pdf_file) as pdf:
        text = "\n".join([page.extract_text() for page in pdf.pages if page.extract_text()])
    return text

def extract_text_from_docx(docx_file):
    text = docx2txt.process(docx_file)
    return text

def review_resume(resume, job_description):
    prompt = f"""
    {template}

    Resume:
    {resume}
    
    Job Description:
    {job_description}
    """
    
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "system", "content": "You are an expert career coach assessing how well a resume matches with the job description and company that is hiring."},
                  {"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )

    result = json.loads(str(response.choices[0].message.content))
    
    return result

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
        # result = review_resume(resume_text, jd_text)
        with open("./sample_result.json", "r") as f:
            result = json.load(f)

        st.subheader("General Feedback", divider="grey")
        st.write(result["general_feedback"])

        st.subheader("Score Breakdown", divider="grey")
        st.write(result["score_breakdown"])

        st.subheader("Top 5 Skills", divider="grey")
        st.write(result["top_5_skills"])

        st.subheader("'Fit' Evaluation", divider="grey")
        st.write(result["fit"]["fit_evaluation"])
        st.write(f"Strengths:")
        for i, strength in enumerate(result["fit"]["strengths"]):
            st.write(f"{i+1}. {strength}")

        st.subheader("Areas for Improvement", divider="grey")
        st.write("Blah blah")

        st.subheader("Resume")
        st.write("Some weak bullet points you can improve on.")
        for i, d in enumerate(result["resume_content"]):
            annotated_text((f"{i+1}. {d['weak_bullet_point']}", ''),)
            for key, val in d["suggestion"].items():
                st.write(f"• **{key}**: {val}")
            st.write(f"**=> Revised Example**: {d['revised_example']}")

        st.subheader("Missing skills/qualifications")
        for item in result["missing_qualifications"]:
            st.write(f":x: {item}")

        st.subheader("Industry Enhancements")
        for item in result["profile_enhancements"]:
            st.write(f":key: {item}")

    else:
        st.warning("Please provide both resume and job description!")
