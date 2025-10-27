#!/bin/bash
set -e

echo "PDF Ingestion Pipeline - End-to-End Test"
echo ""

# Colors
GREEN='\033[0.32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

DOC_ID=""

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PDF_PATH="$SCRIPT_DIR/test_paper.pdf"

# Step 1: Upload PDF
echo -e "${BLUE}Step 1: Uploading test_paper.pdf...${NC}"
RESPONSE=$(curl -s -F "file=@$PDF_PATH" "http://localhost:8001/api/v1/ingest/upload?collection_name=ml_papers")
DOC_ID=$(echo $RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['document_id'])")
echo -e "${GREEN}Uploaded! Document ID: $DOC_ID${NC}"
echo ""

# Step 2: Wait and monitor PostgreSQL
echo -e "${BLUE}Step 2: Monitoring PostgreSQL status...${NC}"
for i in {1..20}; do
    STATUS=$(psql postgresql://postgres:postgres@localhost:5432/ai_systems -t -c "SELECT status FROM documents WHERE id = '$DOC_ID';")
    NUM_CHUNKS=$(psql postgresql://postgres:postgres@localhost:5432/ai_systems -t -c "SELECT num_chunks FROM documents WHERE id = '$DOC_ID';")

    echo "   Attempt $i/20: Status = $STATUS, Chunks = $NUM_CHUNKS"

    if [[ "$STATUS" == *"COMPLETED"* ]]; then
        echo -e "${GREEN}Processing completed!${NC}"
        break
    elif [[ "$STATUS" == *"FAILED"* ]]; then
        ERROR=$(psql postgresql://postgres:postgres@localhost:5432/ai_systems -t -c "SELECT error_message FROM documents WHERE id = '$DOC_ID';")
        echo -e "Processing failed: $ERROR"
        exit 1
    fi

    sleep 2
done
echo ""

# Step 3: Verify PostgreSQL record
echo -e "${BLUE}Step 3: PostgreSQL Record:${NC}"
psql postgresql://postgres:postgres@localhost:5432/ai_systems -c "SELECT id, filename, status, num_pages, num_chunks, file_size FROM documents WHERE id = '$DOC_ID';"
echo ""

# Step 4: Verify MinIO storage
echo -e "${BLUE}Step 4: Checking MinIO storage...${NC}"
python3 << EOF
from minio import Minio

client = Minio(
    "localhost:9000",
    access_key="minioadmin",
    secret_key="minioadmin",
    secure=False
)

# List objects in bucket
objects = client.list_objects("pdf-uploads", prefix="documents/$DOC_ID/", recursive=True)
for obj in objects:
    print(f"Found in MinIO: {obj.object_name} ({obj.size} bytes)")
EOF
echo ""

# Step 5: Verify Weaviate vectors (using REST API)
echo -e "${BLUE}Step 5: Checking Weaviate vectors...${NC}"

# Check schema for collections
COLLECTIONS=$(curl -s "http://localhost:8080/v1/schema" | python3 -c "import sys, json; classes = json.load(sys.stdin).get('classes', []); print(','.join([c['class'] for c in classes]))")
echo "Available collections: $COLLECTIONS"

# Try to find ml_papers collection (case-insensitive)
if echo "$COLLECTIONS" | grep -iq "ml_papers"; then
    # Get actual collection name
    COLLECTION_NAME=$(curl -s "http://localhost:8080/v1/schema" | python3 -c "import sys, json; classes = json.load(sys.stdin).get('classes', []); matches = [c['class'] for c in classes if 'ml_papers' in c['class'].lower()]; print(matches[0] if matches else '')")

    if [ -n "$COLLECTION_NAME" ]; then
        echo "Found collection: $COLLECTION_NAME"

        # Count objects using REST API
        RESPONSE=$(curl -s "http://localhost:8080/v1/objects?class=$COLLECTION_NAME&limit=100")
        COUNT=$(echo "$RESPONSE" | python3 -c "import sys, json; print(len(json.load(sys.stdin).get('objects', [])))")

        echo "Sample query returned $COUNT objects"

        if [ "$COUNT" -gt 0 ]; then
            echo -e "${GREEN}Vectors successfully stored in Weaviate!${NC}"
        else
            echo -e "⚠️  No vectors found - persistence issue detected"
        fi
    else
        echo "Could not determine collection name"
    fi
else
    echo "Collection 'ml_papers' not found"
fi
echo ""

echo -e "${GREEN}End-to-end pipeline test completed!${NC}"
