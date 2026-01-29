"""
PDF to Podcast Generator - Main Orchestrator

A system that transforms long-form documents into two-host podcast scripts
with a verification layer for accuracy and coverage checking.
"""
import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
import yaml
import anthropic

# Load environment variables from .env file
load_dotenv()

from .models import Config, DocumentConfig, SectionConfig
from .extractor import ExtractorAgent
from .generator import generate_script
from .verifier import verify_script
from .pdf_utils import compress_pdf, get_pdf_info


def select_pdf_from_data_dir(data_dir: str = "data") -> str:
    """
    List available PDFs in the data directory and let user select one.

    Args:
        data_dir: Path to the data directory

    Returns:
        Path to selected PDF
    """
    data_path = Path(data_dir)

    # Find all PDFs in data directory
    pdf_files = sorted(data_path.glob("*.pdf"))

    if not pdf_files:
        print(f"Error: No PDF files found in '{data_dir}/' directory")
        print(f"Please add a PDF to the {data_dir}/ directory")
        sys.exit(1)

    if len(pdf_files) == 1:
        selected_pdf = pdf_files[0]
        print(f"Found PDF: {selected_pdf.name}")
        return str(selected_pdf)

    # Multiple PDFs found - ask user to select
    print(f"\nFound {len(pdf_files)} PDF(s) in '{data_dir}/' directory:")
    for i, pdf in enumerate(pdf_files, 1):
        size_mb = pdf.stat().st_size / (1024 * 1024)
        print(f"  {i}. {pdf.name} ({size_mb:.1f} MB)")

    while True:
        choice = input(f"\nSelect a PDF (1-{len(pdf_files)}): ").strip()
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(pdf_files):
                selected_pdf = pdf_files[idx]
                print(f"Selected: {selected_pdf.name}\n")
                return str(selected_pdf)
            else:
                print(f"Invalid choice. Please enter a number between 1 and {len(pdf_files)}")
        except ValueError:
            print(f"Invalid input. Please enter a number between 1 and {len(pdf_files)}")


def load_config(config_path: str) -> Config:
    """Load configuration from YAML file."""
    with open(config_path, "r") as f:
        data = yaml.safe_load(f)

    pdf_path = data["document"]["path"]

    # If PDF is in data directory but doesn't exist, offer selection
    if "data/" in pdf_path and not Path(pdf_path).exists():
        print(f"PDF not found at {pdf_path}")
        pdf_path = select_pdf_from_data_dir()

    # If PDF doesn't exist at all, try selecting from data directory
    elif not Path(pdf_path).exists():
        print(f"PDF not found at {pdf_path}")
        pdf_path = select_pdf_from_data_dir()

    return Config(
        document=DocumentConfig(
            path=pdf_path,
            title=data["document"]["title"]
        ),
        sections=[
            SectionConfig(name=s["name"], pages=s["pages"])
            for s in data["sections"]
        ]
    )


def save_outputs(script_md: str, report_dict: dict, output_dir: str) -> tuple:
    """Save generated outputs to files."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    script_path = output_path / "podcast_script.md"
    report_path = output_path / "verification_report.json"

    with open(script_path, "w") as f:
        f.write(script_md)

    with open(report_path, "w") as f:
        json.dump(report_dict, f, indent=2)

    return script_path, report_path


def run_pipeline(config_path: str, output_dir: str = "output", compress_threshold_mb: float = 10.0) -> None:
    """
    Run the complete PDF-to-Podcast pipeline.

    Args:
        config_path: Path to YAML configuration file
        output_dir: Directory for output files
        compress_threshold_mb: Size threshold in MB above which to auto-compress PDF
    """
    # Check for API key
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY environment variable not set")
        print("Please set it with: export ANTHROPIC_API_KEY='your-key-here'")
        sys.exit(1)

    # Initialize client
    client = anthropic.Anthropic(api_key=api_key)

    # Load configuration
    print(f"\n{'='*60}")
    print("PDF to Podcast Generator")
    print(f"{'='*60}\n")

    print(f"Loading configuration from: {config_path}")
    config = load_config(config_path)
    print(f"Document: {config.document.title}")
    print(f"Sections to cover: {len(config.sections)}")
    for section in config.sections:
        print(f"  - {section.name} (pages {section.pages})")

    # Stage 1: Extraction
    print(f"\n{'-'*60}")
    print("STAGE 1: Document Extraction")
    print(f"{'-'*60}\n")

    extractor = ExtractorAgent(client, compress_threshold_mb=compress_threshold_mb)
    extracted_doc = extractor.extract_document(config)
    print(f"\nExtraction complete: {extracted_doc.total_key_points} key points found")

    # Stage 2: Script Generation
    print(f"\n{'-'*60}")
    print("STAGE 2: Script Generation")
    print(f"{'-'*60}\n")

    script = generate_script(extracted_doc, client)
    print(f"\nScript generated: {script.word_count} words")

    # Stage 3: Verification
    print(f"\n{'-'*60}")
    print("STAGE 3: Verification")
    print(f"{'-'*60}\n")

    report = verify_script(script, extracted_doc, client)

    # Save outputs
    print(f"\n{'-'*60}")
    print("Saving Outputs")
    print(f"{'-'*60}\n")

    script_path, report_path = save_outputs(
        script.to_markdown(),
        report.to_dict(),
        output_dir
    )

    print(f"Script saved to: {script_path}")
    print(f"Verification report saved to: {report_path}")

    # Print summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}\n")

    print(f"Script: {script.title}")
    print(f"Word count: {script.word_count}")
    print(f"\nVerification Results:")
    print(f"  Total claims: {report.total_claims}")
    print(f"  Supported: {report.supported_claims}")
    print(f"  Partially supported: {report.partially_supported_claims}")
    print(f"  Hallucinations: {report.unsupported_claims}")
    print(f"  Support rate: {report.support_rate:.1f}%")
    print(f"\nCoverage: {report.overall_coverage_percentage:.1f}%")

    if report.hallucination_flags:
        print(f"\n⚠️  {len(report.hallucination_flags)} potential hallucination(s) flagged")
        for hf in report.hallucination_flags[:3]:  # Show first 3
            print(f"  - \"{hf.claim[:80]}...\"")

    print(f"\n{'='*60}")
    print("Done!")
    print(f"{'='*60}\n")


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Transform PDF documents into podcast scripts with verification"
    )
    parser.add_argument(
        "--config", "-c",
        default="config.yaml",
        help="Path to configuration YAML file (default: config.yaml)"
    )
    parser.add_argument(
        "--output", "-o",
        default="output",
        help="Output directory (default: output)"
    )
    parser.add_argument(
        "--compress-threshold",
        type=float,
        default=10.0,
        help="PDF size threshold in MB for auto-compression (default: 10.0)"
    )
    parser.add_argument(
        "--compress",
        type=str,
        help="Compress a PDF file and exit (utility mode)"
    )

    args = parser.parse_args()

    # Utility mode: just compress a PDF
    if args.compress:
        info = get_pdf_info(args.compress)
        print(f"PDF: {info['path']}")
        print(f"Size: {info['file_size_mb']:.2f} MB")
        print(f"Pages: {info['page_count']}")
        compress_pdf(args.compress)
        sys.exit(0)

    try:
        run_pipeline(args.config, args.output, args.compress_threshold)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        raise


if __name__ == "__main__":
    main()
