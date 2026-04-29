import sys
import os
from pathlib import Path
import datetime

def ingest_pdf(input_path: Path, output_path: Path):
    try:
        from pypdf import PdfReader
    except ImportError:
        print("Error: 'pypdf' library not found. Install with: pip install pypdf")
        sys.exit(1)

    print(f"Extracting text from PDF: {input_path.name}...")
    reader = PdfReader(input_path)
    content = f"# PDF Source: {input_path.name}\n\n"
    
    for i, page in enumerate(reader.pages):
        text = page.extract_text()
        if text:
            content += f"## Page {i+1}\n{text}\n\n"
    
    output_path.write_text(content, encoding="utf-8")
    print(f"Success: PDF content saved to {output_path}")

def ingest_audio(input_path: Path, output_path: Path):
    try:
        import whisper
    except ImportError:
        print("Error: 'openai-whisper' library not found. Install with: pip install openai-whisper")
        sys.exit(1)

    print(f"Transcribing audio: {input_path.name} (this might take a while)...")
    # Using 'base' model for a balance of speed and accuracy
    model = whisper.load_model("base")
    result = model.transcribe(str(input_path))
    
    content = f"# Audio Transcript: {input_path.name}\n"
    content += f"Date: {datetime.date.today()}\n\n"
    content += result["text"]
    
    output_path.write_text(content, encoding="utf-8")
    print(f"Success: Audio transcription saved to {output_path}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 media_ingest.py <input_file_path>")
        sys.exit(1)

    input_path = Path(sys.argv[1])
    if not input_path.exists():
        print(f"Error: File not found: {input_path}")
        sys.exit(1)

    # Determine paths
    kb_root = Path(__file__).parent.parent
    notes_dir = kb_root / "notes"
    notes_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_name = f"ingested_{input_path.stem}_{timestamp}.md"
    output_path = notes_dir / output_name

    ext = input_path.suffix.lower()
    
    if ext == ".pdf":
        ingest_pdf(input_path, output_path)
    elif ext in [".mp3", ".wav", ".m4a", ".mp4", ".mpeg", ".mpga", ".webm"]:
        ingest_audio(input_path, output_path)
    else:
        print(f"Error: Unsupported file extension: {ext}")
        sys.exit(1)

    print(f"\nNext step: Run following command to add to your Second Brain:")
    print(f"./brain knowledge-base/notes/{output_name}")

if __name__ == "__main__":
    main()
