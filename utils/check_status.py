from fastapi import FastAPI
import uvicorn

app = FastAPI()


@app.get("/check")
def check_status():
    return {'Bot is running...'}


def run_api():
    uvicorn.run(app, host="0.0.0.0", port=8436)
