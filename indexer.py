# RegOps Co-Pilot: Document Indexer v1.1
# Purpose: This script scans for PDFs, extracts text, creates vector embeddings,
#          and saves them to a FAISS index and a JSON mapping file.
#
# Changes in v1.1:
# - Switched from pickle (.pkl) to JSON (.json) for the mapping file for
#   better web browser compatibility.

import os
import fitz  # PyMuPDF
from sentence_transformers import SentenceTransformer
import numpy as np
import faiss
import json

# --- CONFIGURATION ---
PDF_DIRECTORIES = ['.', '_archive']
MODEL_NAME = 'all-MiniLM-L6-v2' 
FAISS_INDEX_FILE = "document_index.faiss"
# --- UPDATED FILE NAME ---
MAPPING_FILE = "document_mapping.json" 
# --- END CONFIGURATION ---

def find_pdf_files(directories):
    pdf_files = []
    for directory in directories:
        if not os.path.exists(directory):
            print(f"Warning: Directory '{directory}' not found. Skipping.")
            continue
        for root, _, files in os.walk(directory):
            for file in files:
                if file.lower().endswith('.pdf'):
                    pdf_files.append(os.path.join(root, file))
    return pdf_files

def extract_text_from_pdf(pdf_path):
    try:
        doc = fitz.open(pdf_path)
        pages_text = []
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            pages_text.append(page.get_text())
        return pages_text
    except Exception as e:
        print(f"Error processing {pdf_path}: {e}")
        return []

def create_chunks_and_mapping(pdf_files):
    chunks = []
    mapping = []
    
    for pdf_path in pdf_files:
        print(f"--> Processing: {pdf_path}")
        pages_text = extract_text_from_pdf(pdf_path)
        for page_num, text in enumerate(pages_text):
            paragraphs = text.split('\n\n')
            for paragraph in paragraphs:
                cleaned_para = paragraph.strip()
                if len(cleaned_para) > 50: # Only index meaningful paragraphs
                    chunks.append(cleaned_para)
                    mapping.append({
                        "source": pdf_path,
                        "page": page_num + 1,
                        "content": cleaned_para
                    })
    return chunks, mapping

def main():
    print("--- Starting Document Indexer v1.1 ---")

    pdf_files = find_pdf_files(PDF_DIRECTORIES)
    if not pdf_files:
        print("No PDF files found. Exiting.")
        return

    print(f"\nFound {len(pdf_files)} PDF files to index.")
    
    chunks, mapping = create_chunks_and_mapping(pdf_files)
    if not chunks:
        print("\nNo text could be extracted from the PDFs. Exiting.")
        return
        
    print(f"\nCreated {len(chunks)} text chunks. Now creating embeddings...")

    model = SentenceTransformer(MODEL_NAME)
    embeddings = model.encode(chunks, show_progress_bar=True)
    
    embeddings = np.array(embeddings).astype('float32')
    
    index = faiss.IndexFlatL2(embeddings.shape[1])
    index.add(embeddings)
    
    print(f"\nEmbeddings created. Saving the index to '{FAISS_INDEX_FILE}'...")
    faiss.write_index(index, FAISS_INDEX_FILE)
    
    print(f"Saving the mapping data to '{MAPPING_FILE}'...")
    # --- THIS IS THE CHANGED LINE: USE JSON INSTEAD OF PICKLE ---
    with open(MAPPING_FILE, 'w', encoding='utf-8') as f:
        json.dump(mapping, f, indent=2)
        
    print("\n--- Indexing Complete! The chatbot 'brain' is ready. ---")

if __name__ == "__main__":
    main()

