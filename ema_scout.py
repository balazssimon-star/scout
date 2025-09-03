# RegOps Co-Pilot: Smart Scout v2.0
# Purpose: This script monitors the EMA eSubmission portal, detects changes
#          to PDF documents, archives old versions, and creates a structured
#          change log.
#
# Changes in v2.0:
# - Uses PyMuPDF (fitz) to read PDF content and generate a hash to detect updates.
# - Archives old PDF versions into an '_archive' directory.
# - Creates a 'change_log.json' that records NEW, UPDATED, and REMOVED events.

import requests
from bs4 import BeautifulSoup
import json
import os
from urllib.parse import urljoin
import hashlib
import datetime
import fitz # PyMuPDF

# --- CONFIGURATION ---
BASE_URL = "https://esubmission.ema.europa.eu/"
# The new log file will track events over time
LOG_FILE = "change_log.json"
# The old file is now used as a state tracker for the last known versions
STATE_FILE = "document_state.json"
# Directory to store old versions of updated documents
ARCHIVE_DIR = "_archive"
# --- END CONFIGURATION ---

def get_pdf_content_hash(pdf_content):
    """Calculates a SHA256 hash for the given PDF content to detect changes."""
    return hashlib.sha2sha256(pdf_content).hexdigest()

def get_current_documents_state():
    """
    Scans the EMA website, downloads PDFs in memory, and returns a dictionary 
    with document names, URLs, and a content hash.
    """
    print(f"--> Fetching documents from: {BASE_URL}")
    try:
        response = requests.get(BASE_URL)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error: Could not fetch the main URL. {e}")
        return None

    soup = BeautifulSoup(response.content, 'html.parser')
    current_state = {}
    
    print("--> Scanning for PDF links...")
    pdf_links = soup.find_all('a', href=lambda href: href and href.endswith('.pdf'))
    print(f"--> Found {len(pdf_links)} PDF links. Processing each one...")

    for link in pdf_links:
        doc_name = link.text.strip()
        doc_url = urljoin(BASE_URL, link['href'])
        
        if doc_name:
            try:
                # Download the PDF content into memory
                pdf_response = requests.get(doc_url, timeout=30)
                pdf_response.raise_for_status()
                pdf_content = pdf_response.content
                
                # Calculate the hash to detect changes
                content_hash = get_pdf_content_hash(pdf_content)
                
                current_state[doc_name] = {
                    "url": doc_url,
                    "hash": content_hash,
                    "content": pdf_content # Keep content for potential archiving
                }
            except requests.exceptions.RequestException as e:
                print(f"  - Warning: Could not download or process '{doc_name}'. Reason: {e}")
            except Exception as e:
                print(f"  - Warning: An unexpected error occurred for '{doc_name}'. Reason: {e}")

    print(f"--> Successfully processed {len(current_state)} documents.")
    return current_state

def read_json_file(filepath):
    """Reads a JSON file if it exists, otherwise returns an empty dictionary/list."""
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {} if filepath == STATE_FILE else []

def write_json_file(data, filepath):
    """Writes data to a JSON file."""
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)

def compare_states(old_state, new_state):
    """
    Compares old and new document states, archives old files on update,
    and returns a list of change events.
    """
    old_docs = set(old_state.keys())
    new_docs = set(new_state.keys())
    
    # Ensure the archive directory exists
    os.makedirs(ARCHIVE_DIR, exist_ok=True)
    
    today_str = datetime.datetime.utcnow().strftime('%Y-%m-%d')
    change_events = []

    # Check for NEW documents
    for doc_name in sorted(new_docs - old_docs):
        event = {
            "date": today_str,
            "type": "NEW",
            "document": doc_name,
            "url": new_state[doc_name]["url"]
        }
        change_events.append(event)
        print(f"  - DETECTED NEW: {doc_name}")

    # Check for REMOVED documents
    for doc_name in sorted(old_docs - new_docs):
        event = {
            "date": today_str,
            "type": "REMOVED",
            "document": doc_name
        }
        change_events.append(event)
        print(f"  - DETECTED REMOVED: {doc_name}")

    # Check for UPDATED documents (same name, different content)
    for doc_name in sorted(old_docs.intersection(new_docs)):
        if old_state[doc_name]['hash'] != new_state[doc_name]['hash']:
            # 1. Archive the OLD version
            archive_filename = f"{today_str}_{doc_name.replace(' ', '_').replace('/', '_')}_old.pdf"
            archive_path = os.path.join(ARCHIVE_DIR, archive_filename)
            
            # We need to fetch the old content again to archive it
            try:
                old_pdf_response = requests.get(old_state[doc_name]['url'], timeout=30)
                if old_pdf_response.ok:
                     with open(archive_path, 'wb') as f:
                        f.write(old_pdf_response.content)
                     print(f"  - ARCHIVED old version of {doc_name} to {archive_path}")
                else:
                    archive_path = None # Failed to archive
            except Exception as e:
                print(f"  - WARNING: Failed to archive old version of {doc_name}. Reason: {e}")
                archive_path = None

            # 2. Create the event log
            event = {
                "date": today_str,
                "type": "UPDATED",
                "document": doc_name,
                "new_url": new_state[doc_name]["url"],
                "archived_old_pdf_path": archive_path
            }
            change_events.append(event)
            print(f"  - DETECTED UPDATE: {doc_name}")
            
    return change_events

def main():
    print("--- Starting Smart Scout v2.0 ---")
    
    previous_state = read_json_file(STATE_FILE)
    current_state = get_current_documents_state()
    
    if current_state is not None:
        print("\n--> Comparing current state with previous state...")
        events = compare_states(previous_state, current_state)
        
        if not events:
            print("--> No changes detected.")
        else:
            print(f"\n--> Found {len(events)} new event(s). Appending to change log.")
            # Append new events to the existing log
            change_log = read_json_file(LOG_FILE)
            change_log.extend(events)
            write_json_file(change_log, LOG_FILE)
        
        # Save the new state for the next run (without the bulky PDF content)
        state_to_save = {
            name: {"url": data["url"], "hash": data["hash"]}
            for name, data in current_state.items()
        }
        write_json_file(state_to_save, STATE_FILE)
        
    print("\n--- Smart Scout Finished ---")

if __name__ == "__main__":
    main()

