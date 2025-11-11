import { Board } from './board.js';
async function simulationMain() {
    const FILENAME = 'boards/ab.txt';
    const PLAYERS = 4;
    const MOVES_PER_PLAYER = 100;
    const MIN_DELAY_MS = 0.1;
    const MAX_DELAY_MS = 2.0;
    const board = await Board.parseFromFile(FILENAME);
    const boardState = board.look('test');
    const headerLine = boardState.split(/\r?\n/, 1)[0] ?? '';
    const m = /^(\d+)x(\d+)$/.exec(headerLine);
    const ROWS = m && m[1] !== undefined ? parseInt(m[1], 10) : 1;
    const COLS = m && m[2] !== undefined ? parseInt(m[2], 10) : 1;
    let successFlips = 0;
    let failedFlips = 0;
    const perPlayer = [];
    const started = Date.now();
    const tasks = [];
    for (let i = 0; i < PLAYERS; i++)
        tasks.push(playerTask(i));
    await Promise.all(tasks);
    const elapsed = Date.now() - started;
    const totalAttempts = PLAYERS * MOVES_PER_PLAYER * 2;
    console.log('simulation finished without crashes');
    console.log(`Players=${PLAYERS}, MovesPerPlayer=${MOVES_PER_PLAYER}, Board=${ROWS}x${COLS}`);
    console.log(`Flip attempts=${totalAttempts}, successes=${successFlips}, failures=${failedFlips}, elapsedMs=${elapsed}`);
    perPlayer.sort((a, b) => a.pid.localeCompare(b.pid));
    for (const s of perPlayer) {
        console.log(`[player ${s.pid}] moves=${s.moves}, elapsedMs=${s.elapsedMs}, successes=${s.successes}, failures=${s.failures}`);
    }
    async function playerTask(index) {
        const pid = `p${index}`;
        let localSuccess = 0;
        let localFail = 0;
        let movesDone = 0;
        const t0 = Date.now();
        for (let move = 0; move < MOVES_PER_PLAYER; move++) {
            try {
                await timeout(randomDelay(MIN_DELAY_MS, MAX_DELAY_MS));
                const r1 = randInt(ROWS), c1 = randInt(COLS);
                await board.flip(pid, r1, c1);
                successFlips++;
                localSuccess++;
            }
            catch {
                failedFlips++;
                localFail++;
            }
            try {
                await timeout(randomDelay(MIN_DELAY_MS, MAX_DELAY_MS));
                const r2 = randInt(ROWS), c2 = randInt(COLS);
                await board.flip(pid, r2, c2);
                successFlips++;
                localSuccess++;
            }
            catch {
                failedFlips++;
                localFail++;
            }
            movesDone++;
        }
        const dt = Date.now() - t0;
        perPlayer.push({ pid, moves: movesDone, elapsedMs: dt, successes: localSuccess, failures: localFail });
    }
}
function randInt(max) {
    return Math.floor(Math.random() * max);
}
function randomDelay(minMs, maxMs) {
    return minMs + Math.random() * (maxMs - minMs);
}
async function timeout(milliseconds) {
    return new Promise((resolve) => setTimeout(resolve, milliseconds));
}
void simulationMain();
//# sourceMappingURL=simulation.js.map