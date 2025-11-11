import test from 'node:test';
import assert from 'node:assert/strict';
import { boardFromCards, countToken, expectReject, withTimeout } from './helpers.js';
import { Board } from '../src/board.js';

test('initial look shows all down', async () => {
  const board = await boardFromCards(2, 2, ['A','A','B','B']);
  const stateA = board.look('alice');
  assert.equal(stateA.split('\n')[0], '2x2');
  assert.equal(countToken(stateA, 'down'), 4);
});

test('1-B first card turns up + controlled (my)', async () => {
  const board = await boardFromCards(2, 2, ['A','A','B','B']);
  await board.flip('alice', 0, 0);
  const sA = board.look('alice');
  assert.ok(sA.includes('\nmy A'));
  const sB = board.look('bob');
  assert.ok(sB.includes('\nup A'));
});

test('2-B fail: second card is currently controlled (same square)', async () => {
  const board = await boardFromCards(2, 2, ['A','A','B','B']);
  await board.flip('alice', 0, 0);
  await expectReject(board.flip('alice', 0, 0), 'currently controlled');
  const sA = board.look('alice');
  assert.ok(sA.includes('\nup A'));
  assert.ok(!sA.includes('\nmy A'));
});

test('1-C first card already up & uncontrolled => take control', async () => {
  const board = await boardFromCards(2, 2, ['A','A','B','B']);
  await board.flip('alice', 0, 0);
  await expectReject(board.flip('alice', 0, 0), 'currently controlled');
  await board.flip('bob', 0, 0);
  const sB = board.look('bob');
  assert.ok(sB.includes('\nmy A'));
});

test('1-D waiting: player waits while card controlled by another, resumes when relinquished', async () => {
  const board = await boardFromCards(1, 2, ['A', 'B']);
  await board.flip('charlie', 0, 0);
  const pBob = board.flip('bob', 0, 0);
  await expectReject(board.flip('charlie', 0, 0), 'currently controlled');
  await pBob;
  const sB = board.look('bob');
  assert.ok(sB.includes('\nmy A'));
});

test('2-A second is empty -> fail; first remains up, uncontrolled', async () => {
  const board = await boardFromCards(1, 2, ['A','B']);
  await board.flip('alice', 0, 0);
  const b2 = await boardFromCards(2, 2, ['A','A','B','B']);
  await b2.flip('alice', 0, 0);
  await b2.flip('alice', 0, 1);
  await b2.flip('alice', 1, 0);
  await b2.flip('bob', 1, 1);
  await expectReject(b2.flip('bob', 0, 0), 'no card at second');
  const sB = b2.look('bob');
  assert.ok(sB.includes('\nup B'));
});

test('2-C turning second card face-up before evaluating match', async () => {
  const board = await boardFromCards(2, 2, ['A','A','B','B']);
  await board.flip('alice', 1, 0);
  const before = board.look('alice');
  assert.ok(before.includes('\ndown'));
  await board.flip('alice', 1, 1);
  const after = board.look('alice');
  const myCount = after.split('\n').filter(l => l.startsWith('my ')).length;
  assert.equal(myCount, 2);
});

test('2-E mismatch leaves both up & uncontrolled; 3-B flips them down at next first', async () => {
  const board = await boardFromCards(2, 2, ['A','A','B','B']);
  await board.flip('alice', 0, 0);
  await board.flip('alice', 1, 0);
  let s = board.look('alice');
  assert.ok(s.includes('\nup A'));
  assert.ok(s.includes('\nup B'));
  await board.flip('alice', 0, 1);
  s = board.look('alice');
  const downs = countToken(s, 'down');
  assert.ok(downs >= 1);
});

test('3-A matched pair removed at next first', async () => {
  const board = await boardFromCards(2, 2, ['A','A','B','B']);
  await board.flip('alice', 0, 0);
  await board.flip('alice', 0, 1);
  await board.flip('alice', 1, 0);
  const s = board.look('alice');
  const lines = s.split('\n').slice(1);
  assert.equal(lines[0], 'none');
  assert.equal(lines[1], 'none');
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

test('mapAll: replaces labels but preserves faceUp/controller state', async () => {
  const board = await boardFromCards(2, 2, ['A','A','B','B']);
  await board.flip('alice', 0, 0);
  await board.flip('bob',   0, 1);
  await board.mapAll(async v => v === 'A' ? 'X' : v);
  const sA = board.look('alice');
  assert.ok(sA.includes('\nmy X'));
  assert.ok(sA.includes('\nup X'));
});
