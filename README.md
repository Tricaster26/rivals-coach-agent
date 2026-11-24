# Rivals Coach Agent (In Progress)

An LLM coaching agent for Marvel Rivals. Given one ranked match and a player, it writes a coaching report: what the player could have known at hero select, what to reflect on after the match, and a few takeaways.

Built with LangGraph, using `openai/gpt-oss-120b` served through Groq. Match data comes from a separate stats backend's `/analysis/*` endpoints.

## Example

A real ranked match, with the data the agent received and the report it wrote. Compare the numbers in the tables with the ones in the report.

### Match data

| | |
| --- | --- |
| Map | Symbiotic Surface (Convergence) |
| Result | Win 3-2, MVP |
| Duration | 16.9 min |
| Hero | Luna Snow (support), whole match |
| Rank tier | Platinum (stats compared with 53,959 platinum+ Luna Snow games) |
| Team split | 2 vanguards, 2 duelists, 2 supports (both teams) |
| Average elo | Your team 4,172, enemy team 4,181 |

**Pick, before the match**

| Expected win rate | Skill win rate on hero | Average matchup vs enemy comp | Season games on hero | Overall win rate |
| --- | --- | --- | --- | --- |
| 47% | 49% | 48% | 19.8 (9.5 W, 10.3 L) | 51% |

**Player stats on Luna Snow**

| Stat | This match | Per min | Usual per min | vs usual | Rank standing | Differs in wins vs losses | This match looks like |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Damage taken | 22,679 | 1,341 | 1,005 | higher | top 3% | yes | losses |
| Damage | 20,003 | 1,183 | 1,016 | higher | top 6% | no | |
| Final hits | 13 | 0.77 | 0.48 | higher | top 6% | no | |
| Kills | 38 | 2.25 | 1.79 | higher | top 7% | yes | wins |
| Deaths | 8 | 0.47 | 0.60 | lower | fewer deaths than 67% of games | yes | wins |
| Solo kills | 1 | 0.06 | 0 | higher | top 18% | | |
| Assists | 31 | 1.83 | 1.53 | in range | around average | yes | wins |
| Healing | 35,354 | 2,090 | 2,035 | in range | around average | no | |

"Usual" is the median of the player's last 20 ranked games on the hero. "Rank standing" compares this game with single games on the hero at the player's rank and above.

**Team totals**

| Stat | Your team | Enemy team | Team gap | Player's share of team |
| --- | --- | --- | --- | --- |
| Damage | 122,144 | 122,985 | −1% | 16% |
| Healing | 92,713 | 85,151 | +9% | 38% |
| Damage taken | 147,586 | 143,631 | +3% | 15% |
| Kills | 208 | 168 | +24% | 18% |
| Deaths | 56 | 78 | −28% | 14% |
| Final hits | 78 | 56 | +39% | 17% |
| Assists | 114 | 88 | +30% | 27% |
| Solo kills | 12 | 7 | +71% | 8% |

### Report

![Coach panel with the report for this match](docs/coach-panel.png)

The report is generated, so it can contain mistakes; spotting them against the tables above is part of how the agent is being improved. In this one, "13 k damage per min" should be 1,341 per min and "22,779 damage" should be 22,679.

## Pipeline

```
fetch_pre → analyze_pre → fetch_post → analyze_post → write_takeaways
```

The pre-match steps only see what was knowable at hero select. The post-match steps add the result and performance, then the last step writes the takeaways.

## Usage

```
python run.py --match <matchId> --player <playerId> [--reasoning low|medium|high]
```

The report is printed and saved, with every step's data, prompt and output, to `runs/<timestamp>-<matchId>/`.

To step through the graph in LangGraph Studio:

```
langgraph dev
```

Start a run with `{"match_id": "...", "player_id": "..."}` as input. Reasoning defaults to `medium`; set `reasoning` in the assistant's configurable to change it. Studio runs save to `runs/<timestamp>-studio/`.
