import os
import pdfplumber
import docx2txt
from openai import OpenAI
import json
import streamlit as st
import time
from dotenv import load_dotenv


load_dotenv()
MODEL = "gpt-4o"
TEMPERATURE = 1.0

# Load OpenAI API Key in .env file
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Load the prompt prepared for resume review
with open("./prompts/career-coach.txt", "r") as f:
    template = f.read()

# Extract text from user's uploaded file
def extract_text(pdf_file=None, docx_file=None):
    """
    Extracts text from the files the user uploads.
    Args:
        pdf_file (UploadedFile): PDF file if present, else None
        docx_file (UploadedFile): DOCX file if present, else None
    Returns:
        (str): Extracted text from file
    """
    if pdf_file is not None:
        with pdfplumber.open(pdf_file) as pdf:
            text = "\n".join([page.extract_text() for page in pdf.pages if page.extract_text()])
    elif docx_file is not None:
        text = docx2txt.process(docx_file)
    return text

# def extract_text_from_pdf(pdf_file):
#     with pdfplumber.open(pdf_file) as pdf:
#         text = "\n".join([page.extract_text() for page in pdf.pages if page.extract_text()])
#     return text

# def extract_text_from_docx(docx_file):
#     text = docx2txt.process(docx_file)
#     return text

def review_resume(resume, job_description):
    """
    Calls OpenAI API with the resume review template.
    Args:
        resume (str): extracted text from resume
        job_desciption (str): extracted text from job description
    Returns:
        (str) OpenAI message content output from prompt.
    """
    prompt = f"""
    {template}

    Resume:
    {resume}
    
    Job Description:
    {job_description}
    """
    
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "system", "content": "You are an expert career coach giving career advice after assessing how well a job searcher's resume matches with the job description and the company that is hiring."},
                  {"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )

    # print(response.choices[0].message.content)
    result = json.loads(str(response.choices[0].message.content))
    return result

# Set up streaming UI for text outputting
def stream_data(text, chart=None):
    """
    Instead of outputting all text at once, streams text word by word at specific delays.
    Args:
        text (str): full text to be streamed
        chart (alt.Chart): altair chart object if present, else None
    Returns:
        None.
    """
    for word in text.split(" "):
        yield word + " "
        time.sleep(0.05)
    
    placeholder = st.empty()

    if chart is not None:
        placeholder.altair_chart(chart)

# Set color for overall match score
def color(score):
    """
    Return color code in alignment with overall match score.
    """
    if score >= 80:
        return "#afa"
    if 75 <= score < 80:
        return "#fea"
    return "#faa"
