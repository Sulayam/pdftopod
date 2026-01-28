"""
PDF Utilities

Utilities for handling PDF documents including compression and optimization.
"""
import os
import shutil
from pathlib import Path
from typing import Optional

import pymupdf


def compress_pdf(
    input_path: str,
    output_path: Optional[str] = None,
    garbage: int = 4,
    deflate: bool = True,
    deflate_images: bool = True,
    deflate_fonts: bool = True,
    clean: bool = True
) -> str:
    """
    Compress a PDF file to reduce its size.

    This function uses PyMuPDF's built-in optimization features to:
    - Remove unused objects (garbage collection)
    - Compress streams using deflate
    - Optimize images and fonts

    Args:
        input_path: Path to the input PDF file
        output_path: Path for the compressed PDF (default: adds '_compressed' suffix)
        garbage: Garbage collection level (0-4, higher = more aggressive)
                 0: No garbage collection
                 1: Remove unreferenced objects
                 2: Also remove unreferenced object groups
                 3: Also merge duplicate objects
                 4: Also merge duplicate stream contents
        deflate: Enable deflate compression for non-image streams
        deflate_images: Enable deflate compression for images
        deflate_fonts: Enable deflate compression for fonts
        clean: Clean and sanitize the PDF

    Returns:
        Path to the compressed PDF file
    """
    input_path = Path(input_path)

    if not input_path.exists():
        raise FileNotFoundError(f"Input PDF not found: {input_path}")

    # Default output path
    if output_path is None:
        output_path = input_path.parent / f"{input_path.stem}_compressed{input_path.suffix}"
    else:
        output_path = Path(output_path)

    # Get original size
    original_size = input_path.stat().st_size

    print(f"[PDF Utils] Compressing: {input_path}")
    print(f"[PDF Utils] Original size: {original_size / 1024 / 1024:.2f} MB")

    # Open and save with compression
    doc = pymupdf.open(str(input_path))

    # Save with optimization options
    doc.save(
        str(output_path),
        garbage=garbage,
        deflate=deflate,
        deflate_images=deflate_images,
        deflate_fonts=deflate_fonts,
        clean=clean
    )

    doc.close()

    # Get compressed size
    compressed_size = output_path.stat().st_size
    reduction = (1 - compressed_size / original_size) * 100

    print(f"[PDF Utils] Compressed size: {compressed_size / 1024 / 1024:.2f} MB")
    print(f"[PDF Utils] Size reduction: {reduction:.1f}%")
    print(f"[PDF Utils] Output: {output_path}")

    return str(output_path)


def get_pdf_info(pdf_path: str) -> dict:
    """
    Get information about a PDF file.

    Args:
        pdf_path: Path to the PDF file

    Returns:
        Dictionary with PDF information
    """
    doc = pymupdf.open(pdf_path)

    info = {
        "path": pdf_path,
        "file_size_mb": os.path.getsize(pdf_path) / 1024 / 1024,
        "page_count": len(doc),
        "title": doc.metadata.get("title", ""),
        "author": doc.metadata.get("author", ""),
        "subject": doc.metadata.get("subject", ""),
        "creator": doc.metadata.get("creator", ""),
        "producer": doc.metadata.get("producer", ""),
        "is_encrypted": doc.is_encrypted,
        "is_pdf": doc.is_pdf,
    }

    doc.close()
    return info


def extract_pages(
    input_path: str,
    output_path: str,
    pages: list[int]
) -> str:
    """
    Extract specific pages from a PDF into a new file.

    Args:
        input_path: Path to the input PDF
        output_path: Path for the extracted pages PDF
        pages: List of page numbers to extract (1-indexed)

    Returns:
        Path to the output PDF
    """
    input_doc = pymupdf.open(input_path)
    output_doc = pymupdf.open()

    for page_num in pages:
        page_idx = page_num - 1  # Convert to 0-indexed
        if 0 <= page_idx < len(input_doc):
            output_doc.insert_pdf(input_doc, from_page=page_idx, to_page=page_idx)
        else:
            print(f"[PDF Utils] Warning: Page {page_num} out of range")

    output_doc.save(output_path)
    output_doc.close()
    input_doc.close()

    print(f"[PDF Utils] Extracted {len(pages)} pages to: {output_path}")
    return output_path


def auto_compress_if_large(
    pdf_path: str,
    threshold_mb: float = 10.0
) -> str:
    """
    Automatically compress a PDF if it exceeds a size threshold.

    Args:
        pdf_path: Path to the PDF file
        threshold_mb: Size threshold in MB above which to compress

    Returns:
        Path to the (possibly compressed) PDF
    """
    size_mb = os.path.getsize(pdf_path) / 1024 / 1024

    if size_mb > threshold_mb:
        print(f"[PDF Utils] PDF size ({size_mb:.1f} MB) exceeds threshold ({threshold_mb} MB)")
        print(f"[PDF Utils] Compressing automatically...")
        return compress_pdf(pdf_path)
    else:
        print(f"[PDF Utils] PDF size ({size_mb:.1f} MB) within threshold, no compression needed")
        return pdf_path


if __name__ == "__main__":
    # CLI for standalone usage
    import argparse

    parser = argparse.ArgumentParser(description="PDF compression utility")
    parser.add_argument("input", help="Input PDF file")
    parser.add_argument("-o", "--output", help="Output PDF file (optional)")
    parser.add_argument("--info", action="store_true", help="Show PDF info only")

    args = parser.parse_args()

    if args.info:
        info = get_pdf_info(args.input)
        print("\nPDF Information:")
        for key, value in info.items():
            print(f"  {key}: {value}")
    else:
        compress_pdf(args.input, args.output)
