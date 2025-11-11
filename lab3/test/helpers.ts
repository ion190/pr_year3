import * as fs from 'node:fs/promises';
import * as os from 'node:os';
import * as path from 'node:path';
import { Board } from '../src/board.js';

export async function boardFromCards(rows: number, cols: number, cards: string[]): Promise<Board> {
  if (cards.length !== rows * cols) throw new Error('bad test: wrong number of cards');
  const dir = await fs.mkdtemp(path.join(os.tmpdir(), 'memscramble-'));
  const file = path.join(dir, 'board.txt');
  const content = `${rows}x${cols}\n` + cards.join('\n') + '\n';
  await fs.writeFile(file, content, 'utf8');
  return Board.parseFromFile(file);
}

/** count lines equal to token (e.g., "down") within a BOARD_STATE string */
export function countToken(boardState: string, token: string): number {
  return boardState.split('\n').slice(1).filter(line => line === token).length;
}

/** expect a promise to reject with a message containing substr */
export async function expectReject(p: Promise<any>, substr: string): Promise<void> {
  let ok = false;
  try { await p; } catch (e: any) {
    if (String(e).includes(substr)) ok = true;
  }
  if (!ok) throw new Error(`expected rejection containing ${JSON.stringify(substr)}`);
}

/** wait for promise with timeout to avoid hanging tests */
export async function withTimeout<T>(p: Promise<T>, ms = 1000): Promise<T> {
  let timer: NodeJS.Timeout;
  const timeout = new Promise<T>((_, rej) => { timer = setTimeout(() => rej(new Error('timeout')), ms); });
  try {
    const v = await Promise.race([p, timeout]);
    // @ts-ignore
    clearTimeout(timer!);
    return v as T;
  } catch (e) {
    // @ts-ignore
    clearTimeout(timer!);
    throw e;
  }
}
