"""
Document Processing Service
Handles PDF and text file extraction, chunking, and preparation for RAG
"""
import os
import uuid
from typing import List, Dict
from dotenv import load_dotenv

load_dotenv()

try:
    from PyPDF2 import PdfReader
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    print("[DOC_PROCESSOR] PyPDF2 not available. PDF processing disabled.")

class DocumentProcessor:
    def __init__(self, chunk_size=500, chunk_overlap=50):
        """
        Initialize document processor
        
        Args:
            chunk_size: Maximum characters per chunk
            chunk_overlap: Characters to overlap between chunks
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        if not PDF_AVAILABLE:
            print("[DOC_PROCESSOR] Warning: PDF processing requires PyPDF2")
    
    def extract_text_from_pdf(self, file_path):
        """
        Extract text from PDF file
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            str: Extracted text
        """
        if not PDF_AVAILABLE:
            raise ValueError("PDF processing not available. Install PyPDF2.")
        
        try:
            reader = PdfReader(file_path)
            text_parts = []
            page_count = len(reader.pages)
            
            print(f"[DOC_PROCESSOR] Processing PDF with {page_count} pages...")
            
            for page_num, page in enumerate(reader.pages):
                try:
                    text = page.extract_text()
                    if text and text.strip():
                        text_parts.append(text)
                        print(f"[DOC_PROCESSOR] Extracted {len(text)} characters from page {page_num + 1}")
                except Exception as e:
                    print(f"[DOC_PROCESSOR] Error extracting page {page_num + 1}: {str(e)}")
                    continue
            
            full_text = "\n\n".join(text_parts)
            print(f"[DOC_PROCESSOR] Total extracted: {len(full_text)} characters from {len(text_parts)} pages")
            
            if not full_text or not full_text.strip():
                raise ValueError("Could not extract meaningful text from PDF. The PDF might be empty, corrupted, or image-based.")
            
            return full_text
            
        except Exception as e:
            print(f"[DOC_PROCESSOR] Error reading PDF: {str(e)}")
            raise
    
    def extract_text_from_file(self, file_path, file_type=None):
        """
        Extract text from file based on type
        
        Args:
            file_path: Path to file
            file_type: Optional file type hint (pdf, txt, etc.)
            
        Returns:
            str: Extracted text
        """
        if not file_type:
            _, ext = os.path.splitext(file_path.lower())
            file_type = ext.lstrip('.')
        
        if file_type == 'pdf':
            return self.extract_text_from_pdf(file_path)
        elif file_type in ['txt', 'text', 'md', 'markdown']:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        else:
            # Try to read as text
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
            except:
                raise ValueError(f"Unsupported file type: {file_type}")
    
    def chunk_text(self, text, metadata=None):
        """
        Split text into chunks with overlap
        
        Args:
            text: Text to chunk
            metadata: Optional metadata dict to attach to each chunk
            
        Returns:
            List[Dict]: List of chunk dicts with 'text', 'id', and 'metadata'
        """
        if not text or not text.strip():
            return []
        
        chunks = []
        start = 0
        chunk_id = 0
        
        # Clean and normalize text
        text = text.strip().replace('\r\n', '\n').replace('\r', '\n')
        
        while start < len(text):
            # Calculate end position
            end = start + self.chunk_size
            
            # Try to break at sentence or paragraph boundary
            if end < len(text):
                # Look for paragraph break first
                para_break = text.rfind('\n\n', start, end)
                if para_break > start:
                    end = para_break + 2
                else:
                    # Look for sentence break
                    sentence_breaks = ['. ', '! ', '? ', '.\n', '!\n', '?\n']
                    best_break = -1
                    for break_char in sentence_breaks:
                        break_pos = text.rfind(break_char, start, end)
                        if break_pos > best_break:
                            best_break = break_pos + len(break_char)
                    if best_break > start:
                        end = best_break
            
            # Extract chunk
            chunk_text = text[start:end].strip()
            
            if chunk_text:
                chunk_metadata = {
                    'chunk_index': chunk_id,
                    'start_char': start,
                    'end_char': end,
                    'chunk_size': len(chunk_text)
                }
                
                # Merge with provided metadata
                if metadata:
                    chunk_metadata.update(metadata)
                
                chunks.append({
                    'id': str(uuid.uuid4()),
                    'text': chunk_text,
                    'metadata': chunk_metadata
                })
                
                chunk_id += 1
            
            # Move start position with overlap
            start = end - self.chunk_overlap
            if start >= len(text):
                break
        
        print(f"[DOC_PROCESSOR] Created {len(chunks)} chunks from text")
        return chunks
    
    def identify_sections(self, text: str) -> List[Dict]:
        """
        Identify sections in the document text
        
        Args:
            text: Full document text
            
        Returns:
            List[Dict]: List of sections with 'title' and 'text' keys
        """
        if not text or not text.strip():
            return []
        
        sections = []
        lines = text.split('\n')
        current_section_title = None
        current_section_text = []
        
        # Pattern 1: Look for heading-like patterns (numbered, all caps, etc.)
        heading_patterns = [
            r'^Chapter \d+',
            r'^Section \d+',
            r'^\d+\.\s+[A-Z]',
            r'^[A-Z][A-Z\s]{3,}$',  # All caps headings
            r'^\d+\.\s+[^\n]{0,100}$',  # Numbered items
        ]
        
        import re
        
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            
            # Skip empty lines at start of section
            if not line_stripped and not current_section_text:
                continue
            
            # Check if line looks like a heading
            is_heading = False
            if line_stripped:
                # Check for heading patterns
                for pattern in heading_patterns:
                    if re.match(pattern, line_stripped):
                        is_heading = True
                        break
                
                # Additional heuristic: short line followed by longer content
                if not is_heading and len(line_stripped) < 80 and len(line_stripped) > 3:
                    # Check next few lines for substantial content
                    next_lines_content = ' '.join(lines[i+1:min(i+4, len(lines))]).strip()
                    if len(next_lines_content) > 100:
                        is_heading = True
            
            if is_heading and current_section_title:
                # Save previous section
                section_text = '\n'.join(current_section_text).strip()
                if section_text:
                    sections.append({
                        'title': current_section_title,
                        'text': section_text
                    })
                current_section_text = []
                current_section_title = line_stripped
            elif is_heading and not current_section_title:
                # First section
                current_section_title = line_stripped
            else:
                # Regular content line
                if current_section_title:
                    current_section_text.append(line)
                else:
                    # No section title yet, accumulate
                    current_section_text.append(line)
                    if not current_section_title and len(current_section_text) > 3:
                        # Use first line as title
                        current_section_title = current_section_text[0].strip() or "Introduction"
                        current_section_text = current_section_text[1:]
        
        # Add final section
        if current_section_title or current_section_text:
            section_text = '\n'.join(current_section_text).strip()
            if section_text:
                sections.append({
                    'title': current_section_title or "Final Section",
                    'text': section_text
                })
        
        # Fallback 1: If no sections found, try chunking-based approach
        if len(sections) == 0:
            print("[DOC_PROCESSOR] No sections identified with heading patterns, trying chunk-based approach...")
            chunks = self.chunk_text(text)
            if chunks:
                # Group chunks into sections (4-6 chunks per section)
                chunks_per_section = max(1, len(chunks) // 5)
                for i in range(0, len(chunks), chunks_per_section):
                    section_chunks = chunks[i:i+chunks_per_section]
                    section_text = '\n\n'.join([c['text'] for c in section_chunks])
                    sections.append({
                        'title': f"Section {len(sections) + 1}",
                        'text': section_text
                    })
        
        # Fallback 2: If still no sections, split text into equal parts
        if len(sections) == 0:
            print("[DOC_PROCESSOR] No sections from chunks, splitting into equal parts...")
            target_sections = 5
            section_length = len(text) // target_sections
            for i in range(target_sections):
                start = i * section_length
                end = (i + 1) * section_length if i < target_sections - 1 else len(text)
                section_text = text[start:end].strip()
                if section_text:
                    sections.append({
                        'title': f"Part {i + 1}",
                        'text': section_text
                    })
        
        # Fallback 3: If still nothing, use entire text as single section
        if len(sections) == 0:
            print("[DOC_PROCESSOR] Using entire document as single section...")
            sections.append({
                'title': "Document Content",
                'text': text
            })
        
        print(f"[DOC_PROCESSOR] Identified {len(sections)} sections")
        return sections
    
    def process_document(self, file_path, document_id=None, document_metadata=None):
        """
        Process a document: extract text and chunk it
        
        Args:
            file_path: Path to document file
            document_id: Optional document ID (generated if not provided)
            document_metadata: Optional metadata dict for the document
            
        Returns:
            Dict: Processed document with chunks
        """
        if not document_id:
            document_id = str(uuid.uuid4())
        
        # Extract text
        text = self.extract_text_from_file(file_path)
        
        # Prepare metadata
        base_metadata = {
            'document_id': document_id,
            'file_path': file_path,
            'file_name': os.path.basename(file_path)
        }
        
        if document_metadata:
            base_metadata.update(document_metadata)
        
        # Chunk text
        chunks = self.chunk_text(text, base_metadata)
        
        return {
            'document_id': document_id,
            'text': text,
            'chunks': chunks,
            'metadata': base_metadata,
            'chunk_count': len(chunks)
        }

