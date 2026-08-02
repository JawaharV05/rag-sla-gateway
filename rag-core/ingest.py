import os
from sentence_transformers import SentenceTransformer
from database import setup_database, get_db_session
from sqlalchemy import text

# Load the free, local embedding model (downloads once, then cached locally)
print("Loading embedding model...")
model = SentenceTransformer('all-MiniLM-L6-v2')
print("Model loaded.")

DOCS_FOLDER = "../data/docs"

def chunk_document(text_content):
    """Split a markdown document into chunks by '##' headers."""
    sections = text_content.split("##")
    chunks = []
    for section in sections:
        section = section.strip()
        if section:  # skip empty pieces
            chunks.append("## " + section if not section.startswith("#") else section)
    return chunks

def ingest_documents():
    setup_database()
    db = get_db_session()

    # Clear existing chunks so re-running this script doesn't create duplicates
    db.execute(text("DELETE FROM chunks;"))
    db.commit()

    files = [f for f in os.listdir(DOCS_FOLDER) if f.endswith(".md")]
    print(f"Found {len(files)} document(s) to process.")

    total_chunks = 0
    for filename in files:
        filepath = os.path.join(DOCS_FOLDER, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        chunks = chunk_document(content)

        for chunk in chunks:
            embedding = model.encode(chunk).tolist()
            db.execute(
                text("""
                    INSERT INTO chunks (source_file, content, embedding)
                    VALUES (:source_file, :content, :embedding)
                """),
                {"source_file": filename, "content": chunk, "embedding": str(embedding)}
            )
            total_chunks += 1

        print(f"  Processed {filename}: {len(chunks)} chunk(s)")

    db.commit()
    db.close()
    print(f"\nDone. Total chunks stored: {total_chunks}")

if __name__ == "__main__":
    ingest_documents()