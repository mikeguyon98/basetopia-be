from google.cloud import firestore
from dotenv import load_dotenv

def migrate_highlights_to_simple_batch():
    load_dotenv()
    db = firestore.Client()
    highlights_ref = db.collection("highlights")
    simple_ref = db.collection("simple_highlights")
    
    # Fetch all docs in one shot (be mindful if the collection is massive).
    all_highlight_docs = list(highlights_ref.stream())
    total_docs = len(all_highlight_docs)
    print(f"Fetched {total_docs} highlight docs.")
    
    BATCH_SIZE = 500
    created_count = 0

    # Process docs in chunks of up to 500
    for i in range(0, total_docs, BATCH_SIZE):
        batch = db.batch()
        chunk = all_highlight_docs[i : i + BATCH_SIZE]

        for doc_snapshot in chunk:
            doc_data = doc_snapshot.to_dict()

            # Extract title from the "highlight" map
            highlight_data = doc_data.get("highlight", {})
            title = highlight_data.get("title", "No title found")

            # Prepare simple_highlights document data
            simple_doc_data = {
                "description": title,
                "video_url": highlight_data.get("video_url", ""),
                "thumbnail": highlight_data.get("image_url", ""),
                "highlight_id": doc_snapshot.id,  # store original doc ID
                "created_at": firestore.SERVER_TIMESTAMP,
            }
            
            # Create a new doc ref in simple_highlights
            new_simple_doc_ref = simple_ref.document()
            
            # Add this write to the batch
            batch.set(new_simple_doc_ref, simple_doc_data)

        # Commit this batch of writes
        batch.commit()
        created_count += len(chunk)
        print(f"Committed batch with {len(chunk)} simple_highlights docs.")

    print(f"Done! Created {created_count} new docs in 'simple_highlights'.")

if __name__ == "__main__":
    migrate_highlights_to_simple_batch()