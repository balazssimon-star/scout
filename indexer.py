# RegOps Co-Pilot: Document Indexer v1.0
# Purpose: This script scans the repository for PDF documents, extracts their text,
#          chunks the text, creates vector embeddings, and saves them to a
#          searchable FAISS index.
#
# This creates the "brain" for our chatbot.

import os
import fitz  # PyMuPDF
from sentence_transformers import SentenceTransformer
import numpy as np
import faiss
import json
import pickle

# --- CONFIGURATION ---
# Directories to scan for PDF files
PDF_DIRECTORIES = ['.', '_archive'] # Scan root and the archive folder
# Name of the pre-trained model to create embeddings
MODEL_NAME = 'all-MiniLM-L6-v2' 
# Output files for the index and the mapping data
FAISS_INDEX_FILE = "document_index.faiss"
MAPPING_FILE = "document_mapping.pkl"
# --- END CONFIGURATION ---

def find_pdf_files(directories):
    """Finds all PDF files in a list of directories."""
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
    """Extracts text from a single PDF, returning text per page."""
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
    """Creates text chunks and a mapping to their source document/page."""
    chunks = []
    mapping = []
    
    for pdf_path in pdf_files:
        print(f"--> Processing: {pdf_path}")
        pages_text = extract_text_from_pdf(pdf_path)
        for page_num, text in enumerate(pages_text):
            # We can use simple paragraph splitting as our chunking strategy
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
    print("--- Starting Document Indexer ---")

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

    # Load the powerful sentence-transformer model
    model = SentenceTransformer(MODEL_NAME)
    
    # Create the vector embeddings. This might take a few minutes.
    embeddings = model.encode(chunks, show_progress_bar=True)
    
    # FAISS requires the embeddings to be in a specific format (float32)
    embeddings = np.array(embeddings).astype('float32')
    
    # Create the FAISS index
    index = faiss.IndexFlatL2(embeddings.shape[1])
    index.add(embeddings)
    
    print(f"\nEmbeddings created. Saving the index to '{FAISS_INDEX_FILE}'...")
    faiss.write_index(index, FAISS_INDEX_FILE)
    
    print(f"Saving the mapping data to '{MAPPING_FILE}'...")
    with open(MAPPING_FILE, 'wb') as f:
        pickle.dump(mapping, f)
        
    print("\n--- Indexing Complete! The chatbot 'brain' is ready. ---")


if __name__ == "__main__":
    main()
```

### **Your Next Steps**

1.  **Save the File:** Save the code above as `indexer.py` in the same main (`root`) directory of your repository as `ema_scout.py`.

2.  **Install the New Libraries:** This script requires powerful new tools. Open your terminal or command prompt and run these commands:
    ```bash
    pip install sentence-transformers
    pip install faiss-cpu
    pip install PyMuPDF
    ```
    *(Note: We use `faiss-cpu` because it's easier to install than the GPU version).*

3.  **Run the Indexer:** From your terminal, in your repository's directory, run the script:
    ```bash
    python indexer.py
    
