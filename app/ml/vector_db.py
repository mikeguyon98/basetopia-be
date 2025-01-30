import getpass
import os
import time
from uuid import uuid4
from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec
from langchain_core.documents import Document
from langchain_google_vertexai import VertexAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from google.cloud import firestore

def get_vertex_embeddings():
    if "GOOGLE_API_KEY" not in os.environ:
        print("GOOGLE_API_KEY not found in environment variables")
        return
    embeddings = VertexAIEmbeddings(model_name="text-multilingual-embedding-002")
    # vector = embeddings.embed_query("hello, world!")
    # print(vector[:5])
    return embeddings


def setup_pinecone():
    if not os.getenv("PINECONE_API_KEY"):
        os.environ["PINECONE_API_KEY"] = getpass.getpass("Enter your Pinecone API key: ")

    pinecone_api_key = os.environ.get("PINECONE_API_KEY")

    pc = Pinecone(api_key=pinecone_api_key)
    index_name = "basetopia-highlights-index"  # change if desired

    existing_indexes = [index_info["name"] for index_info in pc.list_indexes()]

    if index_name not in existing_indexes:
        pc.create_index(
            name=index_name,
            dimension=768,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1"),
        )
        while not pc.describe_index(index_name).status["ready"]:
            time.sleep(1)

    index = pc.Index(index_name)
    embeddings = get_vertex_embeddings()
    vector_store = PineconeVectorStore(index=index, embedding=embeddings)
    return vector_store


def bulk_upload_firestore_highlights_to_pinecone(vector_store, batch_size=500):
    load_dotenv()
    db = firestore.Client()
    highlights_ref = db.collection("highlights")

    # Fetch all highlight documents in bulk
    all_highlight_docs = list(highlights_ref.stream())
    total_docs = len(all_highlight_docs)
    print(f"Fetched {total_docs} highlight docs from Firestore.")

    created_count = 0

    # Process documents in batches
    for i in range(0, total_docs, batch_size):
        batch_docs = all_highlight_docs[i : i + batch_size]
        documents = []

        for doc_snapshot in batch_docs:
            doc_data = doc_snapshot.to_dict()

            # Extract fields for embedding and metadata
            highlight_data = doc_data.get("highlight", {})
            description = highlight_data.get("title", "No title found")
            video_url = highlight_data.get("video_url", "")
            thumbnail = highlight_data.get("image_url", "")
            highlight_id = doc_snapshot.id

            # Create a Document with description as page_content and other fields as metadata
            document = Document(
                page_content=description,
                metadata={
                    "video_url": video_url,
                    "thumbnail": thumbnail,
                    "highlight_id": highlight_id,
                    "source_collection": "highlights",
                },
            )

            documents.append(document)
        

        print(f"Prepared batch {i // batch_size + 1} with {len(documents)} documents for Pinecone upload.")

        # Add documents to Pinecone vector store
        uuids = [str(uuid4()) for _ in documents]
        vector_store.add_documents(documents=documents, ids=uuids)

        created_count += len(documents)
        print(f"Successfully uploaded batch {i // batch_size + 1} to Pinecone ({created_count} docs created).")

    print(f"Done! Created {created_count} new docs in Pinecone.")

def get_vector_store():
    pinecone_api_key = os.environ.get("PINECONE_API_KEY")
    if not pinecone_api_key:
        os.environ["PINECONE_API_KEY"] = getpass.getpass("Enter your Pinecone API key: ")
        pinecone_api_key = os.environ["PINECONE_API_KEY"]
    
    pc = Pinecone(api_key=pinecone_api_key)
    index_name = "basetopia-highlights-index"
    
    # Initialize the Pinecone Index object
    index = pc.Index(index_name)
    
    embeddings = get_vertex_embeddings()
    vector_store = PineconeVectorStore(index=index, embedding=embeddings)
    return vector_store

def main():
    vector_store = setup_pinecone()
    bulk_upload_firestore_highlights_to_pinecone(vector_store)


def test():
    vector_store = get_vector_store()
    docs = vector_store.similarity_search("Kyle Hendricks", k=5)
    for doc in docs:
        print(doc.page_content)

if __name__ == "__main__":
    load_dotenv()
    # main()
    test()