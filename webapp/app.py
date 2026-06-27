import io
import os
import tempfile
import zipfile
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel
from markitdown import MarkItDown

app = FastAPI()
md = MarkItDown()


@app.get("/", response_class=HTMLResponse)
async def index():
    with open(os.path.join(os.path.dirname(__file__), "static", "index.html")) as f:
        return f.read()


@app.post("/convert")
async def convert(file: UploadFile = File(...)):
    suffix = os.path.splitext(file.filename)[1] if file.filename else ""
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        result = md.convert(tmp_path)
        return JSONResponse({"markdown": result.text_content, "filename": file.filename})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        os.unlink(tmp_path)


class FileExport(BaseModel):
    name: str
    markdown: str


@app.post("/download-zip")
async def download_zip(files: list[FileExport]):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in files:
            md_name = os.path.splitext(f.name)[0] + ".md"
            zf.writestr(md_name, f.markdown)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="markitdown-export.zip"'},
    )
