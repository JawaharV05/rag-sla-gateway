import os
from dotenv import load_dotenv
import google.generativeai as genai

# Load variables from the .env file at the project root
load_dotenv(dotenv_path="../.env")

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model_gen = genai.GenerativeModel("gemini-flash-lite-latest")

def generate_answer(question: str, chunks: list, max_tokens: int = 300):
    """Given a question and retrieved chunks, generate a grounded answer using Gemini."""

    context = "\n\n".join(
        f"[Source: {c['source_file']}]\n{c['content']}" for c in chunks
    )

    prompt = f"""You are answering a question using ONLY the provided context below.
If the answer is not clearly in the context, say you don't have enough information.
Do not make anything up.

Context:
{context}

Question: {question}

Answer:"""

    response = model_gen.generate_content(
        prompt,
        generation_config=genai.types.GenerationConfig(max_output_tokens=max_tokens)
    )

    return response.text


if __name__ == "__main__":
    from retrieval import retrieve_chunks

    test_question = "how do I get my password reset?"
    chunks = retrieve_chunks(test_question, top_k=3)
    answer = generate_answer(test_question, chunks)

    print(f"Question: {test_question}\n")
    print(f"Answer: {answer}")