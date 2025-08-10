import os
import time
import random
import shutil
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
port = 4000

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Allowed mime types prefix
ALLOWED_PREFIXES = ("image/", "video/")

@app.post("/upload")
async def upload_file(media: UploadFile = File(...)):
    # Check mimetype
    if not any(media.content_type.startswith(prefix) for prefix in ALLOWED_PREFIXES):
        raise HTTPException(status_code=400, detail="Only images/videos allowed")

    # Check file size (reading file in chunks, limited to 20MB)
    contents = await media.read()
    max_size = 20 * 1024 * 1024  # 20 MB
    if len(contents) > max_size:
        raise HTTPException(status_code=400, detail="File size exceeds 20MB limit")

    # Create unique filename
    unique_suffix = f"{int(time.time())}-{random.randint(0, int(1e9))}"
    extension = os.path.splitext(media.filename)[1]
    filename = f"{media.filename.split('.')[0]}-{unique_suffix}{extension}"
    file_path = os.path.join(UPLOAD_DIR, filename)

    # Write file
    with open(file_path, "wb") as f:
        f.write(contents)

    return JSONResponse({
        "success": True,
        "fileName": filename,
        "originalName": media.filename,
        "mimetype": media.content_type,
        "size": len(contents),
        "filePath": f"/uploads/{filename}"
    })

# To run the server:
# uvicorn filename:app --host 0.0.0.0 --port 4000

# Optionally, serve static files (uploads folder) with:
# from fastapi.staticfiles import StaticFiles
# app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
