import fitz  # PyMuPDF
import docx
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def extract_text_from_file(file_path: Path) -> str:
    """
    Extracts text from a given file (PDF or DOCX).

    Args:
        file_path (Path): The path to the file.

    Returns:
        str: The extracted text.
    """
    text = ""
    try:
        if file_path.suffix == '.pdf':
            with fitz.open(file_path) as doc:
                for page in doc:
                    text += page.get_text()
            logger.info(f"Successfully extracted text from PDF: {file_path.name}")
        elif file_path.suffix == '.docx':
            doc = docx.Document(file_path)
            for para in doc.paragraphs:
                text += para.text + '\n'
            logger.info(f"Successfully extracted text from DOCX: {file_path.name}")
        else:
            logger.warning(f"Unsupported file type: {file_path.suffix}")
            return "Unsupported file type."
    except Exception as e:
        logger.error(f"Error extracting text from {file_path.name}: {e}")
        return f"Error processing file: {e}"

    return text