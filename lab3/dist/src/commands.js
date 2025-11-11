export async function look(board, playerId) {
    return board.look(playerId);
}
export async function flip(board, playerId, row, column) {
    await board.flip(playerId, row, column);
    return board.look(playerId);
}
export async function map(board, playerId, f) {
    await board.mapAll(f);
    return board.look(playerId);
}
export async function watch(board, playerId) {
    await board.watchOnce();
    return board.look(playerId);
}
//# sourceMappingURL=commands.js.map