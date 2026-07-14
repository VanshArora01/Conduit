import re
from app.ai.interfaces.cleaner import BaseCleaner

class PDFCleaner(BaseCleaner):
    def clean(self, text: str) -> str:
        # Remove repeated headers/footers or page numbers (naive approach for demonstration)
        # e.g., Page 1 of 10
        text = re.sub(r'(?i)page \d+ of \d+', '', text)
        text = re.sub(r'^\d+\s*$', '', text, flags=re.MULTILINE)  # orphan numbers
        # Normalize whitespace while preserving paragraphs
        text = re.sub(r'[ \t]+', ' ', text)
        return text.strip()

class MarkdownCleaner(BaseCleaner):
    def clean(self, text: str) -> str:
        # Markdown cleaner can fix broken tables, weird artifacts from conversions
        # Normalize whitespace but preserve structure
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()

class CodeCleaner(BaseCleaner):
    def clean(self, text: str) -> str:
        # Don't strip too much whitespace for code, but perhaps remove trailing spaces
        text = re.sub(r'[ \t]+$', '', text, flags=re.MULTILINE)
        return text.strip()

class SpreadsheetCleaner(BaseCleaner):
    def clean(self, text: str) -> str:
        # Remove empty rows or columns (e.g. ,,,,,,)
        text = re.sub(r'^,+$', '', text, flags=re.MULTILINE)
        text = re.sub(r'\n{2,}', '\n', text)
        return text.strip()

class DefaultCleaner(BaseCleaner):
    def clean(self, text: str) -> str:
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

class CleanerFactory:
    @staticmethod
    def get_cleaner(classification: str) -> BaseCleaner:
        if classification == "PDF":
            return PDFCleaner()
        elif classification == "Markdown":
            return MarkdownCleaner()
        elif classification == "Code":
            return CodeCleaner()
        elif classification == "Spreadsheet":
            return SpreadsheetCleaner()
        else:
            return DefaultCleaner()
