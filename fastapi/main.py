from fastapi import FastAPI
from pyrogue.game import Pyrogue_Game

'''
This, at least for now, is how I'm going to test and verify that PyRogue
as a package is working correctly. Its not super friendly, nor is is meant to be.
This is just to verify that the main game components are working, and that removing
the Tkinter UI hasn't broken anything.

uvicorn main:app --host 0.0.0.0 --port 8080
'''

app = FastAPI()

@app.get("/")
def read_root():
    return {"status": "PyRogue FastAPI application running."}

