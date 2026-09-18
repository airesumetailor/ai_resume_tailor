import asyncio
import re
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from playwright.async_api import async_playwright

# Import AI generator function
from ai_generator import generate_application_data


def sanitize_folder_name(name: str) -> str:
    """Sanitizes company names into valid folder names (e.g., 'Google LLC' -> 'Google_LLC')."""
    if not name:
        return "General"
    cleaned = re.sub(r'[\\/*?:"<>|]', "", name).strip()
    return cleaned.replace(" ", "_") or "General"


def render_html_template(data, context_key, photo_path, template_filename, output_html):
    """Generic Jinja2 HTML template renderer."""
    env = Environment(loader=FileSystemLoader("."))
    template = env.get_template(template_filename)
    
    abs_photo_path = str(Path(photo_path).resolve()) if photo_path else None

    context = {
        context_key: data,
        "photo_path": abs_photo_path
    }

    rendered_html = template.render(**context)

    # Ensure parent output directories exist
    Path(output_html).parent.mkdir(parents=True, exist_ok=True)

    with open(output_html, "w", encoding="utf-8") as f:
        f.write(rendered_html)
        
    print(f"Rendered HTML to {output_html}")
    return output_html


async def convert_html_to_pdf(html_filename, output_pdf, scale=1.0):
    """Converts local HTML to an A4 PDF using Playwright."""
    html_path = Path(html_filename).resolve()
    
    # Ensure destination directory exists
    Path(output_pdf).parent.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        
        await page.goto(f"file:///{html_path}", wait_until="networkidle")
        
        await page.pdf(
            path=output_pdf,
            format="A4",
            print_background=True,
            scale=scale,
            margin={"top": "0px", "right": "0px", "bottom": "0px", "left": "0px"}
        )
        
        await browser.close()
        print(f"Generated PDF: {output_pdf} (Scale: {int(scale * 100)}%)")


async def main():
    base_resume_path = "input/base_resume.json"
    jd_path = "input/jd.txt"
    photo_path = "C:/Users/GREESHMA SS/Downloads/updated p1.JPG"
    
    # 1. Generate tailored data for both resume and cover letter
    print("Generating tailored application content via Gemini...")
    resume_data, cover_letter_data = generate_application_data(base_resume_path, jd_path)

    # 2. Extract Company Name and determine Output Directory
    company_name_raw = (
        cover_letter_data.get("recipient", {}).get("company_name")
        or cover_letter_data.get("recipient", {}).get("company")
        or "General"
    )
    company_folder = sanitize_folder_name(company_name_raw)
    output_dir = Path("output") / company_folder
    output_dir.mkdir(parents=True, exist_ok=True)

    # Define File Paths
    resume_html_path = output_dir / "resume.html"
    resume_pdf_path = output_dir / "Amar_S_Kumar_Resume.pdf"
    
    cover_letter_html_path = output_dir / "cover_letter.html"
    cover_letter_pdf_path = output_dir / "Amar_S_Kumar_Cover_Letter.pdf"

    # 3. Render Resume HTML & PDF
    render_html_template(
        data=resume_data,
        context_key="resume",
        photo_path=photo_path,
        template_filename="resume_template.html",
        output_html=str(resume_html_path)
    )
    await convert_html_to_pdf(
        html_filename=str(resume_html_path),
        output_pdf=str(resume_pdf_path),
        scale=1.12
    )

    # 4. Render Cover Letter HTML & PDF
    render_html_template(
        data=cover_letter_data,
        context_key="cover_letter",
        photo_path=None,
        template_filename="cover_letter_template.html",
        output_html=str(cover_letter_html_path)
    )
    await convert_html_to_pdf(
        html_filename=str(cover_letter_html_path),
        output_pdf=str(cover_letter_pdf_path),
        scale=1.0
    )

if __name__ == "__main__":
    asyncio.run(main())