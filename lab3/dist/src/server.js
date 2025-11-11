import assert from 'node:assert';
import process from 'node:process';
import express from 'express';
import { StatusCodes } from 'http-status-codes';
import { Board } from './board.js';
import { look, flip, map, watch } from './commands.js';
async function main() {
    const [portString, filename] = process.argv.slice(2);
    if (portString === undefined) {
        throw new Error('missing PORT');
    }
    const port = parseInt(portString);
    if (isNaN(port) || port < 0) {
        throw new Error('invalid PORT');
    }
    if (filename === undefined) {
        throw new Error('missing FILENAME');
    }
    const board = await Board.parseFromFile(filename);
    const server = new WebServer(board, port);
    await server.start();
}
/**
 * HTTP web game server.
 */
class WebServer {
    board;
    requestedPort;
    app;
    server;
    constructor(board, requestedPort) {
        this.board = board;
        this.requestedPort = requestedPort;
        this.app = express();
        this.app.use((request, response, next) => {
            // allow requests from web pages hosted anywhere
            response.set('Access-Control-Allow-Origin', '*');
            next();
        });
        /*
         * GET /look/<playerId>
         */
        this.app.get('/look/:playerId', async (request, response) => {
            const { playerId } = request.params;
            assert(playerId);
            const boardState = await look(this.board, playerId);
            response.status(StatusCodes.OK).type('text').send(boardState);
        });
        /*
         * GET /flip/<playerId>/<row>,<column>
         */
        this.app.get('/flip/:playerId/:location', async (request, response) => {
            const { playerId, location } = request.params;
            assert(playerId);
            assert(location);
            const [row, column] = location.split(',').map(s => parseInt(s));
            assert(row !== undefined && !isNaN(row));
            assert(column !== undefined && !isNaN(column));
            try {
                const boardState = await flip(this.board, playerId, row, column);
                response.status(StatusCodes.OK).type('text').send(boardState);
            }
            catch (err) {
                response
                    .status(StatusCodes.CONFLICT) // 409
                    .type('text')
                    .send(`cannot flip this card: ${err}`);
            }
        });
        /*
         * GET /replace/<playerId>/<oldcard>/<newcard>
         */
        this.app.get('/replace/:playerId/:fromCard/:toCard', async (request, response) => {
            const { playerId, fromCard, toCard } = request.params;
            assert(playerId);
            assert(fromCard);
            assert(toCard);
            const boardState = await map(this.board, playerId, async (card) => (card === fromCard ? toCard : card));
            response.status(StatusCodes.OK).type('text').send(boardState);
        });
        /*
         * GET /watch/<playerId>
         */
        this.app.get('/watch/:playerId', async (request, response) => {
            const { playerId } = request.params;
            assert(playerId);
            const boardState = await watch(this.board, playerId);
            response.status(StatusCodes.OK).type('text').send(boardState);
        });
        /*
         * GET /
         */
        this.app.use(express.static('public/'));
    }
    /**
     * Start this server.
     * @returns resolves when the server is listening
     */
    start() {
        return new Promise((resolve, reject) => {
            this.server = this.app.listen(this.requestedPort, '0.0.0.0');
            this.server.once('listening', () => {
                console.log(`server now listening at http://localhost:${this.port}`);
                resolve();
            });
            this.server.once('error', (err) => {
                reject(err);
            });
        });
    }
    /** Actual port after start(). */
    get port() {
        const address = this.server?.address() ?? 'not connected';
        if (typeof address === 'string') {
            throw new Error('server is not listening at a port');
        }
        return address.port;
    }
    /** Stop this server. */
    stop() {
        this.server?.close();
        console.log('server stopped');
    }
}
await main();
//# sourceMappingURL=server.js.map