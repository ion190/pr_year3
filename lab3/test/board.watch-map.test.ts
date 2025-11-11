import test from 'node:test';
import assert from 'node:assert/strict';
import { boardFromCards, withTimeout } from './helpers.js';
import { Board } from '../src/board.js';

test('watchOnce resolves when a card is turned face up', async () => {
  const board = await boardFromCards(1, 2, ['A','B']);
  const w = board.watchOnce();
  await board.flip('alice', 0, 0);
  await withTimeout(w, 500);
});

test('watchOnce resolves when prior mismatched cards are flipped down (3-B)', async () => {
  const board = await boardFromCards(2, 2, ['A','A','B','B']);
  await board.flip('alice', 0, 0);
  await board.flip('alice', 1, 0);
  const w = board.watchOnce();
  await board.flip('alice', 0, 1);
  await withTimeout(w, 500);
});

test('watchOnce resolves when a matched pair is removed (3-A)', async () => {
  const board = await boardFromCards(2, 2, ['A','A','B','B']);
  await board.flip('alice', 1, 0);
  await board.flip('alice', 1, 1);
  const w = board.watchOnce();
  await board.flip('alice', 0, 0);
  await withTimeout(w, 500);
});

test('watchOnce resolves when mapAll changes labels', async () => {
  const board = await boardFromCards(1, 2, ['A','A']);
  const w = board.watchOnce();
  await board.mapAll(async v => v === 'A' ? 'Z' : v);
  await withTimeout(w, 500);
});

test('1-D: waiter resumes after mismatch frees control', async () => {
  const board = await boardFromCards(1, 2, ['A','B']);
  await board.flip('p1', 0, 0);
  const waiter = board.flip('p2', 0, 0);
  await withTimeout((async () => {
    try { await board.flip('p1', 0, 0); } catch { }
  })(), 500);
  await withTimeout(waiter, 500);
  const s = board.look('p2');
  assert.ok(s.includes('\nmy A'));
});
