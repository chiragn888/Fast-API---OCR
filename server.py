from fastapi import FastAPI, Request, File, UploadFile, BackgroundTasks
from fastapi.templating import Jinja2Templates
import shutil
import ocr
import os
import uuid
import json

app = FastAPI()
templates = Jinja2Templates(directory="templates")

@app.get("/")
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api/v1/extract_text")
async def extract_text(image: UploadFile = File(...)):
    temp_file = _save_file_to_disk(image, path="temp", save_as="temp")
    text = ocr.read_image(temp_file)
    return {"filename": image.filename, "text": text}

@app.post("/api/v1/bulk_extract_text")
async def bulk_extract_text(request: Request, bg_task: BackgroundTasks):
    images = await request.form()
    folder_name = 'folder1'
    if os.path.exists(folder_name):
        shutil.rmtree(folder_name) 
        
    os.mkdir(folder_name)

    for image in images.values():
        temp_file = _save_file_to_disk(image, path=folder_name, save_as=image.filename)

    bg_task.add_task(ocr.read_images_from_dir, folder_name, write_to_file=True)
    return {"task_id": folder_name, "num_files": len(images)}

@app.get("/api/v1/bulk_output/{task_id}")
async def bulk_output(task_id):
    text_map = {}
    for file_ in os.listdir(task_id):
        if file_.endswith("txt"):
            text_map[file_] = open(os.path.join(task_id, file_)).read()
    return {"task_id": task_id, "output": text_map}

@app.post("/api/v1/upload_image")
async def upload_image(image: UploadFile = File(...)):
    try:
        file_location = f"images/{image.filename}"
        with open(file_location, "wb") as file:
            shutil.copyfileobj(image.file, file)
        return {"info": f"file '{image.filename}' saved at '{file_location}'"}
    except Exception as e:
        return {"error": str(e)}

@app.delete("/api/v1/delete_file/{filename}")
async def delete_file(filename: str):
    file_location = f"images/{filename}"
    try:
        if os.path.exists(file_location):
            os.remove(file_location)
            return {"info": f"file '{filename}' has been deleted"}
        else:
            return {"error": "file not found"}
    except Exception as e:
        return {"error": str(e)}

def _save_file_to_disk(uploaded_file, path=".", save_as="default"):
    extension = os.path.splitext(uploaded_file.filename)[-1]
    temp_file = os.path.join(path, save_as + extension)
    with open(temp_file, "wb") as buffer:
        shutil.copyfileobj(uploaded_file.file, buffer)
    return temp_file