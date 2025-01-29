from google.cloud import discoveryengine
from google.api_core.client_options import ClientOptions
from dotenv import load_dotenv

if __name__ == "__main__":
    load_dotenv()

    # Configuration
    FIREBASE_PROJECT_ID = "basetopia-b9302"
    GOOGLE_APPLICATION_CREDENTIALS = "basetopia-b9302-firebase-adminsdk-i33cv-50c3703f8d.json"
    LOCATION = "us"  # Default to global if not set
    DATA_STORE_ID = "simple-highlights_1738034163868"  # Ensure this is your actual Data Store ID
    DISCOVERYENGINE_PROJECT_ID = "basetopia-b9302"
    BRANCH = "default_branch"
    COLLECTION_ID = "simple_highlights"
    CHECKPOINT_FILE = "checkpoint.json"
    BATCH_SIZE = 500
    client_options = (
        ClientOptions(api_endpoint=f"{LOCATION}-discoveryengine.googleapis.com")
        if LOCATION != "global"
        else None
    )

    # Create a client
    client = discoveryengine.DocumentServiceClient(client_options=client_options)

    # The full resource name of the search engine branch.
    # e.g. projects/{project}/locations/{location}/dataStores/{data_store_id}/branches/{branch}
    parent = client.branch_path(
        project=FIREBASE_PROJECT_ID,
        location=LOCATION,
        data_store=DATA_STORE_ID,
        branch=BRANCH,
    )

    request = discoveryengine.ImportDocumentsRequest(
        parent=parent,
        firestore_source=discoveryengine.FirestoreSource(
            project_id=FIREBASE_PROJECT_ID,
            database_id="(default)",
            collection_id=COLLECTION_ID,
        ),
        # Options: `FULL`, `INCREMENTAL`
        reconciliation_mode=discoveryengine.ImportDocumentsRequest.ReconciliationMode.INCREMENTAL,
    )

    # Make the request
    operation = client.import_documents(request=request)

    print(f"Waiting for operation to complete: {operation.operation.name}")
    response = operation.result()

    # After the operation is complete,
    # get information from operation metadata
    metadata = discoveryengine.ImportDocumentsMetadata(operation.metadata)

    # Handle the response
    print(response)
    print(metadata)
