import os
from dotenv import load_dotenv
load_dotenv()

import textwrap
import fitz  # pymupdf
from openai import OpenAI

CHEAP_MODEL = "gpt-4o-mini"
client = OpenAI()


def extract_text_from_pdf(pdf_path: str) -> str:
    doc = fitz.open(pdf_path)
    texts = []
    for page in doc:
        texts.append(page.get_text())
    doc.close()
    full_text = "\n".join(texts)
    # light cleanup
    full_text = "\n".join(
        line.strip() for line in full_text.splitlines() if line.strip()
    )
    return full_text


def chunk_text(text: str, max_chars: int = 8000):
    chunks = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + max_chars, n)
        chunks.append(text[start:end])
        start = end
    return chunks


def summarize_pdf(pdf_path: str, label: str = "TEST_PDF") -> str:
    raw_text = extract_text_from_pdf(pdf_path)
    print(f"[INFO] Extracted {len(raw_text)} characters from {pdf_path}")

    # For first test: ONLY summarize the first chunk to keep it super cheap
    chunks = chunk_text(raw_text, max_chars=6000)
    chunks = chunks[:4]
    print(f"[INFO] Summarizing {len(chunks)} chunk(s) with {CHEAP_MODEL}...")

    chunk_summaries = []
    for i, chunk in enumerate(chunks, start=1):
        resp = client.chat.completions.create(
            model=CHEAP_MODEL,
            messages=[
    {
        "role": "system",
        "content": (
            "You are an expert astrophysicist. You write concise but highly technical summaries "
            "of scientific texts. You do not invent facts or numbers; you only use information explicitly "
            "present in the text you are given."
        ),
    },
    {
        "role": "user",
        "content": textwrap.dedent(f"""
        Document label: {label}
        Chunk {i} of {len(chunks)}.

        Task:
        Read the following chunk and write a structured, technical summary of JUST THIS CHUNK.

        Focus on:
        - Scientific context and target(s) mentioned.
        - Observational / experimental setup: facilities (e.g. ALMA), bands, frequencies, spectral setup,
          angular / spectral resolution, sensitivities, integration times if present.
        - Key measurements: radii, velocities, temperatures, column densities, masses, line IDs, S/N, fluxes,
          position angles, inclinations, etc. Include numeric values and units when given.
        - Main results and interpretations that are directly supported by these measurements.
        - Any explicit uncertainties, limits, caveats, or open questions stated in this chunk.

        Constraints:
        - Do NOT speculate or add information that is not explicitly in the text.
        - If the chunk is mostly figures/tables captions, summarize what they quantify (e.g., relation between NT and radius).
        - Write in prose (no bullet lists) and keep the tone appropriate for an expert astrophysicist.

        Chunk text:
        {chunk}
        """).strip(),
    },
            ],
            temperature=0.1,
            max_tokens=900,
        )

        summary = resp.choices[0].message.content.strip()
        print(f"[INFO] Got summary for chunk {i}.")
        chunk_summaries.append(summary)

    # For now, just return the single-chunk summary or join them
    final_summary = "\n\n".join(chunk_summaries)
    return final_summary


if __name__ == "__main__":
    pdf_path = "Papers_PDF/TEST.pdf"  # your TW Hya HC5N proposal
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"Missing PDF at {pdf_path}")

    summary = summarize_pdf(pdf_path, label="TW Hya HC5N ALMA proposal")
    out_path = "TEST_summary.txt"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(summary)
    print(f"[INFO] Summary written to {out_path}")

