from fastapi import FastAPI, HTTPException
import uvicorn
from pydantic import BaseModel
from typing import List
from fastapi.middleware.cors import CORSMiddleware
from connect4 import Connect4
from mcts import ucb2_agent
import copy

app = FastAPI()
game = Connect4()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class GameState(BaseModel):
    board: List[List[int]]
    current_player: int
    valid_moves: List[int]

class AIResponse(BaseModel):
    move: int

class Connect4Agent:
    def __init__(self):
        self.game = Connect4()
        self.strategy = ucb2_agent(3)
        self.pos = self.game.get_initial_position()
        self.old_board = [[0 for _ in range(7)] for _ in range(6)]

    def board_move(self, col, turn):
        for i in range(5, -1, -1):
            if self.old_board[i][col] == 0:
                self.old_board[i][col] = 1 if turn == 0 else 2
                return i
        return None

    #     return move
    def create_position_from_game_state(self, gs: GameState) -> int:
        print("Oldboard la:", self.old_board)
        non_zero_cells = sum(cell != 0 for row in gs.board for cell in row)
        if non_zero_cells == 0:
            self.pos = self.game.get_initial_position()
            self.pos.turn = 0
            self.old_board = [[0 for _ in range(7)] for _ in range(6)]  # reset old_board
            print("Board sau khi refresh (minh di truoc) la:", self.old_board)
        elif non_zero_cells == 1:
            self.pos = self.game.get_initial_position()
            self.old_board = [[0 for _ in range(7)] for _ in range(6)]
            print("Board sau khi refresh (minh di sau) la:", self.old_board)



        # 1) Detect opponent's last move by diffing columns
        opp_move = None
        for col in range(7):
            old_count = sum(1 for r in range(6) if self.old_board[r][col] != 0)
            new_count = sum(1 for r in range(6) if gs.board[r][col] != 0)
            if new_count > old_count:
                opp_move = col
                break

        # 2) If we found their move, apply it to the Position
        if opp_move is not None:
            print("Mask before human makes move: ", self.pos.mask)
            self.pos = self.pos.move(opp_move)
        
        print("Mask after human makes move: ", self.pos.mask)

        # 3) Update our baseline board snapshot
        self.old_board = copy.deepcopy(gs.board)
        print("Board sau khi copy la:", self.old_board)



        # 4) Let the AI choose its move
        ai_move = self.strategy(self.pos)

        # 5) Apply AI move to both Position and old_board
        self.pos = self.pos.move(ai_move)
        # drop AI piece (1) into the lowest empty slot in old_board
        for r in range(5, -1, -1):
            if self.old_board[r][ai_move] == 0:
                self.old_board[r][ai_move] = 2
                break

        return ai_move

connect4agent = Connect4Agent()

@app.post("/api/connect4-move")
async def make_move(game_state: GameState) -> AIResponse:
    try:

        if not game_state.valid_moves:
            raise ValueError("Không có nước đi hợp lệ")
            
        next_move = connect4agent.create_position_from_game_state(game_state)
        print("AI chọn nước:", next_move)
        return AIResponse(move=next_move)
    except Exception as e:
        if game_state.valid_moves:
            print("Có lỗi xảy ra, chọn random:", str(e))
            return AIResponse(move=game_state.valid_moves[0])
        raise HTTPException(status_code=400, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)