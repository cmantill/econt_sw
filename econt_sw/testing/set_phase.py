from i2c import call_i2c

# phase settings found for boards
phase_by_board = {
    2: "6,6,7,7,7,8,7,8,7,8,7,8",
    3: "7,6,8,7,0,8,8,0,8,8,9,8",
    7: "5,4,5,5,6,6,6,6,5,6,6,6",
    8: "5,4,5,5,6,6,6,6,5,6,6,6",
    9: "7,7,7,7,7,7,7,7,7,7,7,7",
    10: "7,7,7,7,7,7,7,7,7,7,7,7",
    11: "7,6,8,8,8,9,8,9,7,8,8,8",
    12: "7,7,7,7,7,7,7,7,7,7,7,7",
    13: "7,7,7,7,7,7,7,7,7,7,7,7",
    14: "7,7,7,7,7,7,7,7,7,7,7,7",
}
def change_phase(board):
    print(f'Set fixed phase {phase_by_board[board]} for board {board}')
    call_i2c(args_name='EPRXGRP_TOP_trackMode',args_value=f'0',args_i2c='ASIC')
    call_i2c(args_name='CH_EPRXGRP_[0-11]_phaseSelect',args_value=f'{phase_by_board[board]}',args_i2c='ASIC')

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--board','-b', required=True, choices=list(phase_by_board.keys()), type=int, help='Board number')
    args = parser.parse_args()

    change_phase(args.board)
