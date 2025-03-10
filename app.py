import streamlit as st
import os
from openai import OpenAI
import pdfplumber
import docx2txt
from dotenv import load_dotenv
from annotated_text import annotated_text
import json
import altair as alt
import polars as pl
import plotly.graph_objects as go
import time

load_dotenv()
MODEL = "gpt-4o"
TEMPERATURE = 1.0

# Load OpenAI API Key in .env file
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Load the prompt prepared for resume review
with open("./prompt.txt", "r") as f:
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
    if score >= 85:
        return "#afa"
    if 70 <= score < 85:
        return "#fea"
    return "#faa"

# Set page config for streamlit UI
st.set_page_config(
    page_title="Resume Review",
    page_icon=":memo:",
    layout="centered",
    initial_sidebar_state="expanded"
)

# Widen default 46rem width of main block
st.html("""
    <style>
        .stMainBlockContainer {
            max-width:60rem;
        }
    </style>
    """
)

# Initialize session state
if ("resume_text" and "jd_text") not in st.session_state:
    st.cache_data.clear()
    st.session_state.resume_text = ""
    st.session_state.jd_text = ""
    st.session_state.uploaded = False

# Set up files upload adjustable sidebar
with st.sidebar:
    st.title("Upload your files")

    uploaded_resume = st.file_uploader("Upload Resume",
                                       type=["pdf", "docx"],
                                       help="Your file or information will not be shared with anyone.",
                                       label_visibility="visible")

    # Upload resume
    resume_text = ""
    if uploaded_resume is not None:
        if uploaded_resume.name.endswith(".pdf"):
            resume_text = extract_text(pdf_file=uploaded_resume)
        elif uploaded_resume.name.endswith(".docx"):
            resume_text = extract_text(docx_file=uploaded_resume)

    uploaded_jd = st.file_uploader("Upload Job Description", type=["pdf", "docx"])

    # Upload job description
    job_desc_text = ""
    if uploaded_jd is not None:
        if uploaded_jd.name.endswith(".pdf"):
            jd_text = extract_text(pdf_file=uploaded_jd)
        elif uploaded_jd.name.endswith(".docx"):
            jd_text = extract_text(docx_file=uploaded_jd)
        # st.success("Job description uploaded and processed!")
    else:
        jd_text = st.text_area("Or paste Job Description:", placeholder="Job description")

    if st.button("Review my resume"):
        if not (resume_text and jd_text):
            st.warning("Please provide both resume and job description.")
        else:
            st.session_state.uploaded = True

# Main block
st.title(":memo: Review My Resume")

# Intro and responsible use notice
# Disappear when user clicks "Review my resume" button
if not st.session_state.uploaded:
    st.write("Welcome to the *Review My Resume* tool!")
    st.write("This tool is built driven by my own desire for a tool that could quickly scan how well I meet the qualifications and skills outlined (sometimes inconspicuously) in (oftentimes) very long job descriptions. Leveraging the use of AI, we can now save a lot of time in the job searching process, making better decision by knowing where we stand, and what we could do to set ourselves apart.")
    with st.expander(":blue[This tool could be useful for you if...]"):
        st.markdown("- **You are applying for a job** and want to know :blue-background[how well your current resume is positioning you to pass the screening round, how to improve, and what strengths to focus on to best represent yourself].\n- **You are looking at your dream job/organization** and want to know :blue-background[where you're lacking and what you can do to better prepare yourself for the position].\n- **You are browsing the job markets** and want to know :blue-background[if your profile matches with the job posting you find interesting, what the industry will look like, and what the pivoting will take].\n- You're the professor or my class's TA, who's reviewing this to grade my final project :D")
    with st.expander(":blue[Some responsible use heads-up...]"):
        st.markdown("- **The score you get is just a measure of how well your resume matches with the JD provided, not an indication of your ability or resume quality**. It is a meaningful input to consider, but is not the only factor for you to decide whether you'll be applying or if you will stand a chance in applying.\n- **Copying and pasting to make yourself look good in your resume is highly advised against**. Consider how you can use these suggestions to better position and improve your authentic self.\n- I have desgined and engineered the prompting based on my experience, past advice from career coaches, and a myriad of job-related workshops. **This tool will provide you with a framework to strategize and speed up your job-related endeavor but is by no means a comprehensive career development advising service**.\n- **No files or information you provided shall be retained or shared**.")
    st.write(":arrow_forward: To begin, start by uploading your resume and JD (or copying and paste) using the sidebar.")
    st.write(":fast_forward: To review another resume or JD, simply remove old files and update with new files using the sidebar.")
    st.write("Best of luck and happy resume reviewing! :sparkles:")

# Change the main block content to analysis
if st.session_state.uploaded:
    # For testing against sample results
    # with open("./sample_result.json", "r") as f:
    #     result = json.load(f)
    with st.spinner("Analyzing in progress..."):
        time.sleep(8)
    result = review_resume(resume_text, jd_text)

    # Overall match score
    overall_score = result["overall_match"]    
    annotated_text("Your resume overall match score against this JD is ", (f"{overall_score}/100", "", color(overall_score)),)
    
    # Analysis tabs
    tab1, tab2, tab3, tab4 = st.tabs(["Overview", "Key Skills Assessment", "Fit Evaluation", "Areas for Improvement"])

    with tab1:
        data = pl.DataFrame(result["score_breakdown"])
        scores_chart = (alt.Chart(data).mark_bar().encode(
            y=alt.Y('category:N', axis=alt.Axis(labelLimit=300), title=''),
            x=alt.X('score:Q', axis=alt.Axis(values=list(range(0, 120, 10))), scale=alt.Scale(domain=[0, 100]))
        ).properties(
            width=800,
            height=300
        ))

        st.write_stream(stream_data(result["general_feedback"], chart=scores_chart))

    with tab2:
        # Reference: https://plotly.com/python/radar-chart/
        skill = []
        score = []
        comment = []
        for item in result["top_5_skills"]:
            skill.append(item["skill"])
            score.append(item["score"])
            comment.append(item["comment"])

        layout = go.Layout(
            margin=go.layout.Margin(
                l=0,
                r=80
            )
        )

        fig = go.Figure(data=go.Scatterpolar(
            r=score,
            theta=skill,
            fill='toself',
            line_width=0,
            name=""
            ), layout=layout
        )

        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 5]
                )
            )
        )

        col1, col2 = st.columns([1.75, 1.25])
        col1.plotly_chart(fig)
        
        comment_container = col2.container(border=True)
        with comment_container:
            for i in range(5):
                st.write_stream(stream_data(f"**{skill[i]}**: {comment[i]}"))

    with tab3:
        st.write_stream(stream_data(result["fit"]["fit_evaluation"]))
        st.write_stream(stream_data(f"Here are some key strengths you possess that will be highly valued in this role:"))
        for i, strength in enumerate(result["fit"]["strengths"]):
            st.write_stream(stream_data(f"{i+1}. {strength}"))

    with tab4:
        st.subheader("Resume")
        st.write_stream(stream_data("We have identified some weak bullet points in your resume that you can improve on."))
        for i, d in enumerate(result["resume_content"]):
            time.sleep(0.1)
            annotated_text((f"{i+1}. {d['weak_bullet_point']}", ''),)
            for key, val in d["suggestion"].items():
                st.write_stream(stream_data(f"• ***{key}***: {val}"))
            st.write_stream(stream_data(f"**=> Revised Example**: {d['revised_example']}"))

        st.subheader("Missing skills/qualifications")
        st.write_stream(stream_data("Here are some qualifications and skills mentioned in the JD that you have not shown to have. Generally, to present a strong case, you would want to check most (missing 1-2 might be fine) if not all of the required qualifications."))
        for item in result["missing_qualifications"]:
            st.write_stream(stream_data(f":x: {item}"))

        st.subheader("Industry Enhancements")
        st.write_stream(stream_data(result["profile_enhancements"]["industry_trend"]))
        st.write_stream(stream_data(result["profile_enhancements"]["career_advice"]))
        for item in result["profile_enhancements"]["action_steps"]:
            st.write_stream(stream_data(f":key: {item}"))
