import tiktoken
import re
from typing import List
from app.ai.interfaces.chunking import BaseChunker, ChunkDict
from app.ai.config import ai_config

def count_tokens(text: str) -> int:
    try:
        encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(text))
    except Exception:
        # Fallback approximation (roughly 4 chars per token)
        return len(text) // 4

def build_chunk(content: str, section_title: str | None = None, page_number: int | None = None) -> ChunkDict:
    return {
        "content": content.strip(),
        "token_count": count_tokens(content),
        "character_count": len(content),
        "section_title": section_title,
        "page_number": page_number
    }

class RecursiveChunker(BaseChunker):
    """
    Splits text by paragraphs, then sentences if paragraphs are too long, with overlap.
    """
    def __init__(self, chunk_size: int = ai_config.DEFAULT_CHUNK_SIZE, overlap: int = ai_config.DEFAULT_CHUNK_OVERLAP):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, text: str) -> List[ChunkDict]:
        # Using characters as an approximation since original used len()
        # To be completely accurate with tokens, we'd count tokens per piece.
        # For simplicity and performance, we'll use character limits: 1 token ~= 4 chars
        max_chars = self.chunk_size * 4
        overlap_chars = self.overlap * 4
        
        paragraphs = [p for p in text.split("\n\n") if p.strip()]
        chunks = []
        current_chunk = []
        current_length = 0
        
        for p in paragraphs:
            # If a single paragraph is too large, split by sentence
            pieces = [p]
            if len(p) > max_chars:
                pieces = [s.strip() for s in re.split(r'(?<=[.!?]) +', p) if s.strip()]
                
            for piece in pieces:
                if current_length + len(piece) > max_chars and current_chunk:
                    # Save current chunk
                    chunk_text = "\n\n".join(current_chunk)
                    chunks.append(build_chunk(chunk_text))
                    
                    # Create next chunk with overlap
                    # Keep popping from start of current_chunk until length is <= overlap_chars
                    while current_length > overlap_chars and len(current_chunk) > 1:
                        removed = current_chunk.pop(0)
                        current_length -= len(removed) + 2 # +2 for "\n\n"
                        
                current_chunk.append(piece)
                current_length += len(piece) + (2 if len(current_chunk) > 1 else 0)
                
        if current_chunk:
            chunk_text = "\n\n".join(current_chunk)
            chunks.append(build_chunk(chunk_text))
            
        return chunks

class MarkdownChunker(BaseChunker):
    def chunk(self, text: str) -> List[ChunkDict]:
        sections = re.split(r'(^#+ .*$)', text, flags=re.MULTILINE)
        chunks = []
        current_title = None
        current_content = ""
        
        for section in sections:
            if section.startswith('#'):
                if current_content.strip():
                    chunks.append(build_chunk(current_content, current_title))
                current_title = section.strip()
                current_content = section.strip() + "\n"
            else:
                current_content += section
                
        if current_content.strip():
            chunks.append(build_chunk(current_content, current_title))
            
        return chunks

class CodeChunker(BaseChunker):
    def chunk(self, text: str) -> List[ChunkDict]:
        lines = text.split("\n")
        chunks = []
        current_chunk = ""
        chunk_size_chars = ai_config.DEFAULT_CHUNK_SIZE * 4
        
        for line in lines:
            if len(current_chunk) + len(line) <= chunk_size_chars:
                current_chunk += line + "\n"
            else:
                chunks.append(build_chunk(current_chunk))
                current_chunk = line + "\n"
                
        if current_chunk:
            chunks.append(build_chunk(current_chunk))
            
        return chunks

class SpreadsheetChunker(BaseChunker):
    def chunk(self, text: str) -> List[ChunkDict]:
        lines = text.split("\n")
        chunks = []
        block = []
        
        current_sheet = None
        
        for line in lines:
            if line.startswith("--- Sheet:"):
                if block:
                    chunks.append(build_chunk("\n".join(block), current_sheet))
                    block = []
                current_sheet = line.replace("--- Sheet:", "").replace("---", "").strip()
                continue
                
            block.append(line)
            if len(block) >= 50:
                chunks.append(build_chunk("\n".join(block), current_sheet))
                block = []
                
        if block:
            chunks.append(build_chunk("\n".join(block), current_sheet))
            
        return chunks

class SentenceChunker(BaseChunker):
    def chunk(self, text: str) -> List[ChunkDict]:
        sentences = re.split(r'(?<=[.!?]) +', text.replace('\n', ' '))
        return [build_chunk(s) for s in sentences if s.strip()]

class ChunkerFactory:
    @staticmethod
    def get_chunker(classification: str) -> BaseChunker:
        if classification == "PDF":
            return RecursiveChunker()
        elif classification == "Markdown":
            return MarkdownChunker()
        elif classification == "Code":
            return CodeChunker()
        elif classification == "Spreadsheet":
            return SpreadsheetChunker()
        elif classification == "Plain Text":
            return RecursiveChunker()
        else:
            return RecursiveChunker()
