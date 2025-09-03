import requests
from bs4 import BeautifulSoup
import json
import os
from urllib.parse import urljoin

# The URL of the EMA eSubmission portal we are monitoring
BASE_URL = "https://esubmission.ema.europa.eu/"
# The local file where we will store the list of found documents
LOG_FILE = "document_log.json"

def get_current_documents():
    """Scans the EMA website and returns a dictionary of all found PDF documents."""
    print(f"--> Fetching documents from: {BASE_URL}")
    try:
        response = requests.get(BASE_URL)
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
    except requests.exceptions.RequestException as e:
        print(f"Error: Could not fetch the URL. {e}")
        return None

    soup = BeautifulSoup(response.content, 'html.parser')
    
    documents = {}
    # Find all anchor tags (<a>) which have an 'href' attribute ending in '.pdf'
    for link in soup.find_all('a', href=lambda href: href and href.endswith('.pdf')):
        doc_name = link.text.strip()
        # Make sure the link is a full URL
        doc_url = urljoin(BASE_URL, link['href'])
        
        if doc_name:
            documents[doc_name] = doc_url
            
    print(f"--> Found {len(documents)} PDF documents.")
    return documents

def read_log_file():
    """Reads the previous list of documents from the local log file."""
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def write_log_file(documents):
    """Writes the current list of documents to the local log file."""
    with open(LOG_FILE, 'w', encoding='utf-8') as f:
        json.dump(documents, f, indent=4)

def compare_documents(old_docs, new_docs):
    """Compares the old and new document lists and prints the differences."""
    old_set = set(old_docs.keys())
    new_set = set(new_docs.keys())

    added_docs = new_set - old_set
    removed_docs = old_set - new_set

    if not added_docs and not removed_docs:
        print("\n--> No changes detected.")
    else:
        if added_docs:
            print("\n--- NEW Documents Found ---")
            for doc in sorted(added_docs):
                print(f"- {doc}")
        
        if removed_docs:
            print("\n--- REMOVED Documents ---")
            for doc in sorted(removed_docs):
                print(f"- {doc}")

def main():
    """Main function to run the scout."""
    print("--- Starting EMA Scout ---")
    
    # Get the previous state from our log file
    previous_documents = read_log_file()
    
    # Get the current state from the live website
    current_documents = get_current_documents()
    
    if current_documents is not None:
        # Compare the two states
        compare_documents(previous_documents, current_documents)
        
        # Save the new state for the next run
        write_log_file(current_documents)
        
    print("\n--- EMA Scout Finished ---")

if __name__ == "__main__":
    main()

