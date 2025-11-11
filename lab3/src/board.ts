import * as fs from "node:fs";

type Coord = { r: number; c: number };

type Spot = {
  card: string;
  faceUp: boolean;
  controller: string | null;
};

type PlayerState = {
  controlled: Coord[];
  lastFaceUps: Coord[];
};

// gives a Promise and the ability to resolve/reject it from the outside later
class Deferred<T> {
  promise: Promise<T>;
  resolve!: (v: T) => void;
  reject!: (e?: any) => void;
  constructor() {
    this.promise = new Promise<T>((res, rej) => {
      this.resolve = res; this.reject = rej;
    });
  }
}

export class Board {
  private readonly rows: number;
  private readonly cols: number;
  private readonly grid: (Spot | null)[][];
  private readonly players: Map<string, PlayerState> = new Map();

  // fulfill when a card turns up/down, is removed, or its string changes
  private changeWatchers: Deferred<void>[] = [];

  // waiters wanting control for a (r,c) currently controlled by someone else
  // key is `${r},${c}`
  private readonly controlWaiters: Map<string, Deferred<void>[]> = new Map();

  private constructor(rows: number, cols: number, cards: string[]) {
    this.rows = rows;
    this.cols = cols;
    this.grid = Array.from({ length: rows }, (_, r) =>
      Array.from({ length: cols }, (_, c) => {
        const card = cards[r * cols + c]!;
        return { card, faceUp: false, controller: null } as Spot;
      })
    );
    this.checkRep();
  }

  static async parseFromFile(filename: string): Promise<Board> {
    const raw = await fs.promises.readFile(filename, "utf8");
    const norm = raw.replace(/\r\n/g, "\n").replace(/\r/g, "\n");
    let lines = norm.split("\n");
    if (lines.length > 0 && lines[lines.length - 1] === "") lines = lines.slice(0, -1);

    if (lines.length < 1) throw new Error("invalid board file: missing size line");

    const header = lines[0]!.trim();
    const m = header.match(/^(\d+)x(\d+)$/);
    if (!m) throw new Error("invalid board header, expected ROWxCOLUMN");
    const rows = parseInt(m[1]!, 10);
    const cols = parseInt(m[2]!, 10);
    if (!(rows > 0 && cols > 0)) throw new Error("rows/cols must be positive");

    const expected = rows * cols;
    const cards = lines.slice(1);

    if (cards.length !== expected) {
      throw new Error(`invalid board file: expected ${expected} cards, got ${cards.length}`);
    }

    for (const c of cards) {
      if (c.length === 0) throw new Error("invalid board file: empty card line");
      if (!/^[^\s\n\r]+$/.test(c)) {
        throw new Error(`illegal card: ${JSON.stringify(c)}`);
      }
    }

    return new Board(rows, cols, cards);
  }


  look(playerId: string): string {
    this.requirePlayerId(playerId);
    const lines: string[] = [`${this.rows}x${this.cols}`];
    for (let r = 0; r < this.rows; r++) {
      for (let c = 0; c < this.cols; c++) {
        const spot = this.at(r, c);
        if (spot === null) {
          lines.push("none");
        } else if (!spot.faceUp) {
          lines.push("down");
        } else if (spot.controller === playerId) {
          lines.push(`my ${spot.card}`);
        } else {
          lines.push(`up ${spot.card}`);
        }
      }
    }
    return lines.join("\n");
  }

  async flip(playerId: string, row: number, column: number): Promise<void> {
    this.requirePlayerId(playerId);
    this.requireInBounds(row, column);

    await this.finishPreviousPlayIfNecessary(playerId);

    const ps = this.getPlayer(playerId);

    if (ps.controlled.length === 0) {
      // FIRST card
      const wait = await this.tryFirstCard(playerId, row, column);
      if (!wait) return; // success or fail already handled
      // 1-D: need to wait because card is controlled by another player
      await wait.promise;
      return this.flip(playerId, row, column);
    } else if (ps.controlled.length === 1) {
      // SECOND card
      await this.trySecondCard(playerId, row, column);
      return;
    } else {
      // Defensive: if a pair is still controlled, finish it and reattempt
      await this.finishPreviousPlayIfNecessary(playerId);
      return this.flip(playerId, row, column);
    }
  }

  async mapAll(transform: (card: string) => Promise<string>): Promise<void> {
    // Collect distinct values -> coordinates
    const groups = new Map<string, Coord[]>();
    for (let r = 0; r < this.rows; r++) {
      for (let c = 0; c < this.cols; c++) {
        const spot = this.at(r, c);
        if (spot) {
          const list = groups.get(spot.card) ?? [];
          list.push({ r, c });
          groups.set(spot.card, list);
        }
      }
    }

    for (const [value, coords] of groups.entries()) {
      const newVal = await transform(value);
      if (!/^[^\s\n\r]+$/.test(newVal)) {
        throw new Error(`map() produced illegal card ${JSON.stringify(newVal)} for input ${JSON.stringify(value)}`);
      }
      let changed = false;
      for (const { r, c } of coords) {
        const spot = this.at(r, c);
        if (spot && spot.card !== newVal) {
          spot.card = newVal;
          changed = true;
        }
      }
      if (changed) this.notifyChange();
    }
    this.checkRep();
  }

  /** Wait until the next board change (single-shot). */
  async watchOnce(): Promise<void> {
    const d = new Deferred<void>();
    this.changeWatchers.push(d);
    return d.promise;
  }



  private async finishPreviousPlayIfNecessary(playerId: string): Promise<void> {
    const ps = this.getPlayer(playerId);

    // if they currently control a matched pair (2 cards) remove them
    if (ps.controlled.length === 2) {
      for (const { r, c } of ps.controlled) {
        if (this.at(r, c) !== null) {
          this.grid[r]![c] = null;
          // wake any waiters for this location
          this.releaseWaiters(r, c);
        }
      }
      ps.controlled = [];
      this.notifyChange();
      this.checkRep();
    }

    // flip down prior non-matching face-ups (still up & uncontrolled)
    if (ps.lastFaceUps.length > 0) {
      let changed = false;
      for (const { r, c } of ps.lastFaceUps) {
        const spot = this.at(r, c);
        if (spot && spot.faceUp && spot.controller === null) {
          spot.faceUp = false;
          changed = true;
        }
      }
      ps.lastFaceUps = [];
      if (changed) {
        this.notifyChange();
        this.checkRep();
      }
    }
  }

  /**
   * Try first card.
   * @returns null if finished (success/fail handled), or a Deferred to wait
   */
  private async tryFirstCard(playerId: string, r: number, c: number): Promise<Deferred<void> | null> {
    const spot = this.at(r, c);
    if (spot === null) {
      throw new Error("no card at location");
    }
    if (!spot.faceUp) {
      // turn up and take control
      spot.faceUp = true;
      spot.controller = playerId;
      this.getPlayer(playerId).controlled = [{ r, c }];
      this.notifyChange();
      this.checkRep();
      return null;
    }
    // spot is face up
    if (spot.controller === null || spot.controller === playerId) {
      // remains face up; take control
      spot.controller = playerId;
      this.getPlayer(playerId).controlled = [{ r, c }];
      this.checkRep();
      return null;
    }
    // if face up ad controlled by another then wait
    const key = `${r},${c}`;
    const d = new Deferred<void>();
    const q = this.controlWaiters.get(key) ?? [];
    q.push(d);
    this.controlWaiters.set(key, q);
    return d;
  }

  private async trySecondCard(playerId: string, r: number, c: number): Promise<void> {
    const ps = this.getPlayer(playerId);
    const first = ps.controlled[0]!;
    const firstSpot = this.at(first.r, first.c);

    if (!firstSpot) {
      ps.controlled = [];
      return;
    }

    const spot = this.at(r, c);
    if (spot === null) {
      // second is empty -> fail, relinquish first
      firstSpot.controller = null;
      ps.controlled = [];
      ps.lastFaceUps = [{ r: first.r, c: first.c }];
      this.releaseWaiters(first.r, first.c);
      this.checkRep();
      throw new Error("no card at second location");
    }

    if (spot.faceUp && spot.controller !== null) {
      // controlled by someone (maybe self) then fail and relinquish first
      firstSpot.controller = null;
      ps.controlled = [];
      ps.lastFaceUps = [{ r: first.r, c: first.c }];
      this.releaseWaiters(first.r, first.c);
      this.checkRep();
      throw new Error("second card is currently controlled");
    }

    // if second is face down, turn it face up
    if (!spot.faceUp) {
      spot.faceUp = true;
      this.notifyChange();
    }

    // evaluate match
    if (spot.card === firstSpot.card) {
      // success, keep control of both (remain face up)
      spot.controller = playerId;
      firstSpot.controller = playerId;
      ps.controlled = [first, { r, c }];
      this.checkRep();
    } else {
      // mismatch, relinquish control, both remain face up
      firstSpot.controller = null;
      spot.controller = null;
      ps.controlled = [];
      ps.lastFaceUps = [first, { r, c }];
      this.releaseWaiters(first.r, first.c);
      this.releaseWaiters(r, c);
      this.checkRep();
    }
  }

  private releaseWaiters(r: number, c: number) {
    const key = `${r},${c}`;
    const q = this.controlWaiters.get(key);
    if (q && q.length > 0) {
      const toWake = q.splice(0, q.length);
      for (const d of toWake) d.resolve();
    }
  }

  private notifyChange() {
    const watchers = this.changeWatchers.splice(0, this.changeWatchers.length);
    for (const w of watchers) w.resolve();
  }

  private getPlayer(id: string): PlayerState {
    this.requirePlayerId(id);
    let ps = this.players.get(id);
    if (!ps) {
      ps = { controlled: [], lastFaceUps: [] };
      this.players.set(id, ps);
    }
    return ps;
  }

  private requireInBounds(r: number, c: number) {
    if (!Number.isInteger(r) || !Number.isInteger(c) || r < 0 || c < 0 || r >= this.rows || c >= this.cols) {
      throw new Error("row/column out of bounds");
    }
  }

  private requirePlayerId(id: string) {
    if (typeof id !== "string" || !/^[A-Za-z0-9_]+$/.test(id)) {
      throw new Error("invalid player id");
    }
  }

  /** Safe access that erases `undefined` for strict TS configs. */
  private at(r: number, c: number): Spot | null {
    return this.grid[r]![c] as Spot | null;
  }

  private checkRep() {
    if (!(this.rows > 0 && this.cols > 0)) throw new Error("RI: bad dimensions");
    if (this.grid.length !== this.rows) throw new Error("RI: grid height mismatch");
    for (let r = 0; r < this.rows; r++) {
      const row = this.grid[r]!;
      if (row.length !== this.cols) throw new Error("RI: grid width mismatch");
      for (let c = 0; c < this.cols; c++) {
        const spot = row[c] as Spot | null;
        if (spot) {
          if (spot.faceUp === false && spot.controller !== null) {
            throw new Error("RI: faceDown cannot have a controller");
          }
          if (spot.controller !== null && !/^[A-Za-z0-9_]+$/.test(spot.controller)) {
            throw new Error("RI: invalid controller id");
          }
        }
      }
    }
    // Players' controlled cards are consistent
    for (const [pid, ps] of this.players.entries()) {
      for (const { r, c } of ps.controlled) {
        const spot = this.at(r, c);
        if (!spot || !spot.faceUp || spot.controller !== pid) {
          throw new Error("RI: player controlled set inconsistent with grid");
        }
      }
    }
  }
}
