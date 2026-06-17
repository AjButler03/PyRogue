from fastapi import FastAPI
from pyrogue.game import Pyrogue_Game

'''
This, at least for now, is how I'm going to test and verify that PyRogue
as a package is working correctly. Its not super friendly, nor is is meant to be.
This is just to verify that the main game components are working, and that removing
the Tkinter UI hasn't broken anything.

uvicorn api.main:app --host 0.0.0.0 --port 8080
'''

app = FastAPI()

@app.get("/")
def read_root():
    return {"status": "PyRogue FastAPI application running."}

@app.get("/test_start_game")
def test_start_game():
    game = Pyrogue_Game(80, 24, 0.5)
    
    return {"status": "Game started successfully."}