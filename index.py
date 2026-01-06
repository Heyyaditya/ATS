from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import PyPDF2
from google import genai
from google.genai import types
import json, os

app = Flask(__name__, template_folder="../templates")
CORS(app)

# ❌ remove dotenv completely (Vercel ignores it)

# ✅ GEMINI KEY must come from Vercel dashboard
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY not set")

client = genai.Client(api_key=GEMINI_API_KEY)

# ---------------- PDF TEXT EXTRACTION ----------------
def extract_text_from_pdf(file_stream):
    text = ""
    reader = PyPDF2.PdfReader(file_stream)
    for page in reader.pages:
        if page.extract_text():
            text += page.extract_text() + "\n"
    return text.strip()

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/analyze", methods=["POST"])
def analyze():
    if "resume" not in request.files:
        return jsonify({"error": "No resume uploaded"}), 400

    resume_file = request.files["resume"]
    jd = request.form.get("job_description", "")

    resume_text = extract_text_from_pdf(resume_file)
    if not resume_text:
        return jsonify({"error": "Could not read resume"}), 400

    prompt = f"""
Return ONLY valid JSON:
{{
  "score": number,
  "skills": [string],
  "analysis": [
    {{
      "title": string,
      "status": "pass" | "warn" | "fail",
      "desc": string
    }}
  ]
}}

RESUME:
{resume_text}

JOB DESCRIPTION:
{jd if jd else "N/A"}
"""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )

        data = json.loads(response.text)
        return jsonify(data)

    except Exception as e:
        return jsonify({
            "score": 0,
            "skills": [],
            "analysis": [{
                "title": "Analysis Error",
                "status": "fail",
                "desc": str(e)
            }]
        }), 500
 
