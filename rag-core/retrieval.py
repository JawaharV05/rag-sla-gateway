from sentence_transformers import SentenceTransformer
from database import get_db_session
from sqlalchemy import text

model = SentenceTransformer('all-MiniLM-L6-v2')

def retrieve_chunks(question: str, top_k: int = 5):
    """Given a question, return the top_k most relevant chunks from the database."""
    question_embedding = model.encode(question).tolist()

    db = get_db_session()
    result = db.execute(
        text("""
            SELECT source_file, content, embedding <=> CAST(:embedding AS vector) AS distance
            FROM chunks
            ORDER BY distance
            LIMIT :top_k
        """),
        {"embedding": str(question_embedding), "top_k": top_k}
    )

    chunks = []
    for row in result:
        chunks.append({
            "source_file": row.source_file,
            "content": row.content,
            "distance": float(row.distance)
        })

    db.close()
    return chunks


if __name__ == "__main__":
    # Quick manual test
    test_question = "how do I get my password reset?"
    results = retrieve_chunks(test_question, top_k=3)
    print(f"Question: {test_question}\n")
    for i, chunk in enumerate(results, 1):
        print(f"{i}. [{chunk['source_file']}] (distance: {chunk['distance']:.4f})")
        print(f"   {chunk['content'][:100]}...\n")