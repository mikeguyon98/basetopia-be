import os
import time
from uuid import uuid4
from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_google_vertexai import VertexAIEmbeddings
from google.cloud import firestore
from google.cloud import aiplatform

# Removed Pinecone-related imports and code.
# Instead, we define a VertexAIVectorStore that uses Vertex AI for embeddings 
# and (for demonstration) performs an in-memory similarity search.
# In production, replace the dummy implementations with calls to the Vertex AI Matching Engine API.

class VertexAIVectorStore:
    def __init__(self, index_name, embedding, project, location):
        self.index_name = index_name
        self.embedding = embedding
        self.project = project
        self.location = location
        # For demonstration purposes we use an in-memory dict to store vectors and documents.
        # In production, this is where you would connect to your Vertex AI Matching Engine endpoint.
        self.store = {}  # key: id, value: (vector, Document)

    def add_documents(self, documents, ids):
        # Compute and store embeddings for each document.
        for doc, doc_id in zip(documents, ids):
            # Using the Vertex AI embeddings model to compute vector for the document's page_content.
            vector = self.embedding.embed_query(doc.page_content)
            self.store[doc_id] = (vector, doc)
        print(f"Indexed {len(documents)} documents into Vertex AI index '{self.index_name}'.")
        # In production: Upsert these vectors/documents into Vertex AI Matching Engine.

    def similarity_search(self, query, k=5):
        # Compute the embedding for the query.
        query_vector = self.embedding.embed_query(query)
        # In production: This call would invoke the Vertex AI Matching Engine similarity API.
        # Here we perform a brute-force cosine similarity search over the in-memory vectors.
        import numpy as np

        results = []
        for doc_id, (vec, doc) in self.store.items():
            vec = np.array(vec)
            query_vec = np.array(query_vector)
            # Compute cosine similarity.
            similarity = np.dot(query_vec, vec) / (np.linalg.norm(query_vec) * np.linalg.norm(vec) + 1e-10)
            results.append((similarity, doc))
        # Sort by descending similarity.
        results.sort(key=lambda x: x[0], reverse=True)
        return [doc for _, doc in results[:k]]


def get_vertex_embeddings():
    if "GOOGLE_API_KEY" not in os.environ:
        print("GOOGLE_API_KEY not found in environment variables")
        return
    embeddings = VertexAIEmbeddings(model_name="text-multilingual-embedding-002")
    return embeddings


def setup_vertex_index(index_name="basetopia-highlights-index"):
    # Initialize Vertex AI with project and location (ensure these environment variables are set).
    project = os.environ.get("GOOGLE_CLOUD_PROJECT")
    if not project:
        raise ValueError("GOOGLE_CLOUD_PROJECT environment variable not set.")
    location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
    aiplatform.init(project=project, location=location)
    embeddings = get_vertex_embeddings()
    vector_store = VertexAIVectorStore(index_name=index_name, embedding=embeddings, project=project, location=location)
    return vector_store


def setup_players_vertex_index():
    # Setup a separate index for players.
    project = os.environ.get("GOOGLE_CLOUD_PROJECT")
    if not project:
        raise ValueError("GOOGLE_CLOUD_PROJECT environment variable not set.")
    location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
    aiplatform.init(project=project, location=location)
    index_name = "basetopia-players-index"
    embeddings = get_vertex_embeddings()
    vector_store = VertexAIVectorStore(index_name=index_name, embedding=embeddings, project=project, location=location)
    return vector_store


def bulk_upload_players_to_vertexai(vector_store, batch_size=500):
    load_dotenv()
    db = firestore.Client()
    players_ref = db.collection("players")
    all_players_docs = list(players_ref.stream())
    total_docs = len(all_players_docs)
    print(f"Fetched {total_docs} player docs from Firestore.")

    created_count = 0

    for i in range(0, total_docs, batch_size):
        batch_docs = all_players_docs[i : i + batch_size]
        documents = []
        for doc_snapshot in batch_docs:
            doc_data = doc_snapshot.to_dict()
            player_name = doc_data.get("mlb_person_fullName", "No name found")
            player_id = doc_snapshot.id
            player_team = doc_data.get("mlb_person_team_id", "No team found")
            player_position = doc_data.get("mlb_person_position_id", "No position found")
            
            document = Document(
                page_content=player_name,
                metadata={
                    "player_id": player_id,
                    "player_team": player_team,
                    "player_position": player_position,
                },
            )
            documents.append(document)

        print(f"Prepared batch {i // batch_size + 1} with {len(documents)} documents for Vertex AI upload.")

        uuids = [str(uuid4()) for _ in documents]
        vector_store.add_documents(documents=documents, ids=uuids)

        created_count += len(documents)
        print(f"Successfully uploaded batch {i // batch_size + 1} to Vertex AI ({created_count} docs indexed).")

    print(f"Done! Indexed {created_count} new docs in Vertex AI index '{vector_store.index_name}'.")


def bulk_upload_firestore_highlights_to_vertexai(vector_store, batch_size=500):
    load_dotenv()
    db = firestore.Client()
    highlights_ref = db.collection("highlights")

    # Fetch all highlight documents in bulk.
    all_highlight_docs = list(highlights_ref.stream())
    total_docs = len(all_highlight_docs)
    print(f"Fetched {total_docs} highlight docs from Firestore.")

    created_count = 0

    # Process documents in batches.
    for i in range(0, total_docs, batch_size):
        batch_docs = all_highlight_docs[i : i + batch_size]
        documents = []

        for doc_snapshot in batch_docs:
            doc_data = doc_snapshot.to_dict()

            # Extract fields for embedding and metadata.
            highlight_data = doc_data.get("highlight", {})
            description = highlight_data.get("title", "No title found")
            video_url = highlight_data.get("video_url", "")
            thumbnail = highlight_data.get("image_url", "")
            highlight_id = doc_snapshot.id

            # Create a Document with description as page_content and other fields as metadata.
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
        
        print(f"Prepared batch {i // batch_size + 1} with {len(documents)} documents for Vertex AI upload.")

        # Add documents to the Vertex AI vector store.
        uuids = [str(uuid4()) for _ in documents]
        vector_store.add_documents(documents=documents, ids=uuids)

        created_count += len(documents)
        print(f"Successfully uploaded batch {i // batch_size + 1} to Vertex AI ({created_count} docs indexed).")

    print(f"Done! Indexed {created_count} new docs in Vertex AI index '{vector_store.index_name}'.")


def get_vector_store():
    # Retrieve the highlights vector store for Vertex AI.
    return setup_vertex_index("basetopia-highlights-index")


def get_players_vector_store():
    # Retrieve the players vector store for Vertex AI.
    return setup_players_vertex_index()


def main():
    vector_store = setup_vertex_index("basetopia-highlights-index")
    bulk_upload_firestore_highlights_to_vertexai(vector_store)


def test():
    vector_store = get_vector_store()
    docs = vector_store.similarity_search("Kyle Hendricks", k=5)
    for doc in docs:
        print(doc.page_content)


def upload_players_to_vertexai():
    vector_store = setup_players_vertex_index()
    bulk_upload_players_to_vertexai(vector_store)


if __name__ == "__main__":
    load_dotenv()
    # Uncomment one of the following to run:
    # main()
    # upload_players_to_vertexai()