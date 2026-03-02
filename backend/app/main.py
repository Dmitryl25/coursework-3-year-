from fastapi import FastAPI
from api import auth, ocr, diary, food

app = FastAPI(title="Food Backend")

app.include_router(auth.router, prefix='/auth', tags=["Auth"])
app.include_router(ocr.router, prefix='/ocr', tags=["OCR"])
app.include_router(diary.router, prefix='/diary', tags=["Diary"])
app.include_router(food.router, prefix='/food', tags=["Food"])

@app.get("/")
async def root():
    return {"message": "Evertthing is good"}


