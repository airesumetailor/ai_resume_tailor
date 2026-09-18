import json
import os
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# 1. Concrete key-value pairs for skills instead of list[list[str]]
class SkillCategory(BaseModel):
    category: str = Field(description="Skill area, e.g., Cloud & Data")
    values: str = Field(description="Comma separated list of skills")


# 2. Strict Education schema instead of dict[str, str]
class EducationEntry(BaseModel):
    degree: str
    institution: str
    year: str


class Header(BaseModel):
    name: str
    title: str
    location: str
    phone: str
    email: str
    work_rights: str


class ExperienceEntry(BaseModel):
    company: str
    role: str
    dates: str
    location: str
    bullets: list[str]


class ResumeSchema(BaseModel):
    header: Header
    summary: str
    skills: list[SkillCategory]  # Explicit Pydantic list model
    experience: list[ExperienceEntry]
    education: list[EducationEntry]  # Explicit Pydantic list model


class Recipient(BaseModel):
    hiring_manager: str
    company_name: str
    address: str


class CoverLetterSchema(BaseModel):
    header: Header
    recipient: Recipient
    subject: str
    salutation: str
    paragraphs: list[str]
    closing: str
    signature_name: str


class TailoredApplicationOutput(BaseModel):
    resume: ResumeSchema
    cover_letter: CoverLetterSchema


def generate_application_data(base_resume_path, jd_path):
    client = genai.Client()

    with open(base_resume_path, "r", encoding="utf-8") as f:
        base_resume = json.load(f)

    with open(jd_path, "r", encoding="utf-8") as f:
        job_description = f.read()

    prompt = f"""
    You are an expert career strategist and technical resume writer.
    Tailor the candidate's base resume and generate a cover letter aligned with the provided Job Description.

    BASE RESUME DATA:
    {json.dumps(base_resume, indent=2)}

    TARGET JOB DESCRIPTION:
    {job_description}

    "Do not use em-dashes (—) or en-dashes (–) in the output text. Use standard hyphens (-) or commas for punctuation instead."
    """

    # Pass the Pydantic class directly to response_schema
    response = client.models.generate_content(
        model="gemini-3.5-flash-lite",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=TailoredApplicationOutput,
            temperature=0.2,
            # Disables tool execution logic to silence the AFC warning:
            # function_calling_config=types.FunctionCallingConfig(
            #     mode=types.FunctionCallingConfigMode.NONE
            # ),
        ),
    )

    data = json.loads(response.text)

    # Convert SkillCategory objects back to list format for ReportLab rendering if needed
    if "skills" in data["resume"]:
        data["resume"]["skills"] = [
            [s["category"], s["values"]] for s in data["resume"]["skills"]
        ]
    else:
        # If Gemini returned no skills or an empty list/dict, fallback to base_resume skills
        data["resume"]["skills"] = base_resume.get("skills", [])

    return data["resume"], data["cover_letter"]


if __name__ == "__main__":
    resume_data, cover_letter_data = generate_application_data(
        base_resume_path="input/base_resume.json",
        jd_path="input/jd.txt"
    )

    os.makedirs("input", exist_ok=True)
    with open("input/resume_content.json", "w", encoding="utf-8") as f:
        json.dump(resume_data, f, indent=2)

    with open("input/cover_letter_content.json", "w", encoding="utf-8") as f:
        json.dump(cover_letter_data, f, indent=2)

    print("Successfully generated input/resume_content.json and input/cover_letter_content.json!")