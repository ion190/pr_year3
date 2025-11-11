import { Board } from "./board.js";

export async function look(board: Board, playerId: string): Promise<string> {
  return board.look(playerId);
}


export async function flip(
  board: Board,
  playerId: string,
  row: number,
  column: number
): Promise<string> {
  await board.flip(playerId, row, column);
  return board.look(playerId);
}


export async function map(
  board: Board,
  playerId: string,
  f: (card: string) => Promise<string>
): Promise<string> {
  await board.mapAll(f);
  return board.look(playerId);
}


export async function watch(board: Board, playerId: string): Promise<string> {
  await board.watchOnce();
  return board.look(playerId);
}
