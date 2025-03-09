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
        messages=[{"role": "system", "content": "You are an expert career coach assessing how well a job searcher's resume matches with the job description and company that is hiring."},
                  {"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )

    # print(response.choices[0].message.content)
    result = json.loads(str(response.choices[0].message.content))
    return result

# Streaming UI
def stream_data(text, chart=None):
    for word in text.split(" "):
        yield word + " "
        time.sleep(0.05)
    
    placeholder = st.empty()

    if chart is not None:
        placeholder.altair_chart(chart)

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

with st.sidebar:
    st.title("Upload your files")

    uploaded_resume = st.file_uploader("Upload resume", type=["pdf", "docx"], help="Your file or information will not be shared with anyone.", label_visibility="visible")

    resume_text = ""
    if uploaded_resume is not None:
        if uploaded_resume.name.endswith(".pdf"):
            resume_text = extract_text_from_pdf(uploaded_resume)
        elif uploaded_resume.name.endswith(".docx"):
            resume_text = extract_text_from_docx(uploaded_resume)

    uploaded_jd = st.file_uploader("Upload job description", type=["pdf", "docx"])

    job_desc_text = ""
    if uploaded_jd is not None:
        if uploaded_jd.name.endswith(".pdf"):
            jd_text = extract_text_from_pdf(uploaded_jd)
        elif uploaded_jd.name.endswith(".docx"):
            jd_text = extract_text_from_docx(uploaded_jd)
        # st.success("Job description uploaded and processed!")
    else:
        jd_text = st.text_area("Or paste Job Description:")

    if st.button("Review"):
        if not (resume_text and jd_text):
            st.warning("Please provide both resume and job description!")
        else:
            st.session_state.uploaded = True

st.title(":memo: Review My Resume")
# Disappear when user clicks "review"
if not st.session_state.uploaded:
    st.write("Intro and some responsible AI stuff goes here.")

if st.session_state.uploaded:
    with open("./sample_result.json", "r") as f:
        result = json.load(f)
    # result = review_resume(resume_text, jd_text)

    overall_score = result["overall_match"]
    def color(score):
        if score >= 85:
            return "#afa"
        if 70 <= score < 85:
            return "#fea"
        return "#faa"
    
    with st.spinner("Analyzing in progress..."):
        time.sleep(4)
    
    annotated_text("Your resume overall match score against this JD is ", (f"{overall_score}/100", "", color(overall_score)),)
    
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
        st.write_stream(stream_data(f"Strengths:"))
        for i, strength in enumerate(result["fit"]["strengths"]):
            st.write_stream(stream_data(f"{i+1}. {strength}"))

    with tab4:
        st.subheader("Resume")
        st.write_stream(stream_data("Some weak bullet points you can improve on."))
        for i, d in enumerate(result["resume_content"]):
            time.sleep(0.1)
            annotated_text((f"{i+1}. {d['weak_bullet_point']}", ''),)
            for key, val in d["suggestion"].items():
                st.write_stream(stream_data(f"• **{key}**: {val}"))
            st.write_stream(stream_data(f"**=> Revised Example**: {d['revised_example']}"))

        st.subheader("Missing skills/qualifications")
        for item in result["missing_qualifications"]:
            st.write_stream(stream_data(f":x: {item}"))

        st.subheader("Industry Enhancements")
        st.write_stream(stream_data(result["profile_enhancements"]["industry_trend"]))
        st.write_stream(stream_data(result["profile_enhancements"]["career_advice"]))
        for item in result["profile_enhancements"]["action_steps"]:
            st.write_stream(stream_data(f":key: {item}"))