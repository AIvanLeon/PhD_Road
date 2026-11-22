# Bet Advisor (Liga MX + Premier League)

A weekly Telegram message with a lean for every Liga MX match in the next 7 days, based **only on the current tournament** (no past seasons).

## Files

- `leagues/liga_mx.json`, `leagues/premier_league.json` — Per-league settings (ESPN league code, table zones, model weights/thresholds). Every script takes `--league <name>` (default `liga_mx`)
- `match_details.py` — Per-match DraftKings odds (1X2, Over/Under), team shots/shots on target/red cards and player stats from ESPN's summary endpoint; finished matches cached in `data/match_cache/`
- `fetch_data.py` — Pulls the season's matches from ESPN's public API (no key) and computes the table and last-N form; run directly for a table preview
- `players.py` — Top scorers/assisters per team and last-match availability flags
- `build_message.py` — Rates each fixture and writes `data/message.txt`
- `backtest.py` — Replays the season so far and scores every pick the model would have made
- `liguilla.py` — Playoff model + replay of every Liguilla since Clausura 2024 (`python liguilla.py`)
- `send_telegram.py` — Sends it (skips quietly if the message is empty) via `@PhDork_bot` (same bot/secrets as the other reminders)

## Model

Rating per team = **points per game over the last 4 matches + 0.1 × shots-on-target difference per game over the same 4** (early jornadas just use whatever has been played), with a small **+0.1 home advantage**. Only the current tournament feeds the rating; past tournaments are used only to check which settings hold up (`python backtest.py --all`). Plus, in the **last 3 rounds only** (ramping up to the final jornada): +0.3 if fighting for the top 8, +0.15 if already in but racing for a top-4 seed or 1st, −0.2 if clinched with nothing to gain or eliminated.

Pick from the rating gap:

| Gap | Pick |
|---|---|
| ≤ 0.2 | Draw |
| ≤ 0.35 | Double chance (favourite win or draw) |
| > 0.7 | Favourite win |
| in between | No bet (lean shown, not backed) |

Dropped after backtesting (no help or worse): home/away splits, full-season points, goal difference, short-rest penalty, missing-key-player penalty, Over/Under lean, medium-edge win picks.

**Key players**: each team's top 3 by goals + assists this season, flagged ⚠️ if they were not in the last match squad, got a red card, or were an unused sub (lineups only come out ~1 h before kickoff, so this is the best pre-match signal). In Apertura 2026, teams whose top scorer didn't play got 0.97 pts/game vs 1.42 when he did; the ⚠️ flag was right 18/31 times. Display only: adding it to the rating as a penalty (top scorer only, each of top 3, or scaled by share of team goals) made every backtest variant worse (+38.7u → +3.7u to +33.1u), mostly by spoiling draw picks — the flag is wrong ~40% of the time, and the odds likely already price in confirmed absences.

## Premier League

Same model, separate settings tuned on 2024-25 → 2026-27 (`python backtest.py --all --league premier_league`; odds from Jan 2026):

- **Form over the last 8 games** (≈ the same share of a 38-game season as 4 of 17 in Liga MX) + 0.1 × shots-on-target difference, **home advantage 0.2**.
- **Table zones** (each is a "top-k" line the team can still cross): title (1), Champions League (4), Europa League (5), survival (17, i.e. avoid the bottom 3). In the last 6 matchweeks a team with any zone still open gets a bonus; one with nothing left gets a penalty.
- **Motivation rule** (last 6 matchweeks): if only one side still has something to play for → double chance on that side. Better teams normally lose 27% of games; motivated better teams lost 3/32 (9%); the rule went 36/41.

Backtest, all 837 matches: win picks 54%, double chance 71%, last-6-weeks picks 67/98 (+11.2u on 51 with odds); overall about break-even at the odds (+0.5u on 269). Draws were unusually common in 2025-26 and 2026-27 (≈30% vs ≈25% priced in), which is why "always bet the draw" shows a profit — don't read it as an edge.

## Liguilla

Rules (Apertura 2026): top 8, no play-in; 1v8, 2v7, 3v6, 4v5, two legs, **no away goals**. The higher seed hosts leg 2 and, in quarterfinals and semifinals, **goes through on a tied aggregate**; the final goes to extra time + penalties.

| Match | Pick | Since Clausura 2024 |
|---|---|---|
| Leg 1 (higher seed away) | Double chance lower seed (home) | 28/35 (80%) |
| Leg 2, higher seed level or up 1 | Double chance higher seed | 13/16 (81%) |
| Leg 2, higher seed down | Higher seed win (must attack; levelling is enough) | 9/13 (69%) |
| Leg 2, higher seed up ≥ 2 (`big_lead`) | Higher seed win (rival needs a 3+ goal win) | 0/1 — too rare to judge |
| Final, leg 2 | Regular form model (no seed advantage) | 2/4 |

If leg 2 is in the same weekly window as an unplayed leg 1, the message shows both branches. Only Clausura 2026 has odds, so profit is barely measurable (+1.5u on 16 bets). The extra-time/penalty final leg is excluded from scoring.

## Backtest

`python backtest.py` goes through every finished regular-season match (from jornada 2 on), rebuilds the table from **only the matches played before kickoff**, makes the pick, and checks it against the real result. A win pick counts if that team wins; a draw pick only on a draw; a close-game pick counts if the favored side doesn't lose; Over/Under counts against the 2.5 line. Each pick is also settled at the DraftKings odds ESPN stored for that match (1 unit flat stake; double chance priced from the 1X2 odds), so the output shows profit/ROI alongside hit rate. It compares against baselines (bookmaker favourite, always draw, always home, higher-ranked team), and writes each match to `data/backtest.json`. The weekly message includes a one-line season record from the same replay.

Home advantage was first dropped because Apertura 2026 was unusual (home teams won 37%, vs 46–50% in 2024–2025). Tuned on 2024–2025 instead, 0.1–0.15 slightly improved draw and double-chance hit rates; kept small at 0.1.

Matches that kicked off less than `kickoff_grace_minutes` (7) ago are still included, so a late-built message doesn't drop a game that just started.

## Usage

```bash
python fetch_data.py        # preview the computed table
python build_message.py     # builds data/message.txt
python backtest.py          # how the model would have done this season
python backtest.py --all    # every tournament since Clausura 2024 (odds only from 2026)
python build_message.py --league premier_league
python backtest.py --all --league premier_league
python send_telegram.py     # sends it
```

Runs every Thursday via `.github/workflows/weekly-bet-advisor.yml` (or manually from the Actions tab), sending one message per league (Premier League only on Thursdays), plus Mondays with `--liguilla-only` for Liga MX, which only sends when there are Liguilla matches that week. ESPN scoreboards for finished months are cached in `data/scoreboard_cache/`.
