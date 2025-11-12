import asyncio
import time
import sys

sys.path.append(r"c:\Users\codyr\DiscordBots\Allspark")

from Systems.PnW.MA.query import PNWAPIQuery


async def main():
    q = PNWAPIQuery()

    home_names = [
        "Commonwealth Defense Force",
        "UNION OF BURMA",
        "Cybertr0n",
        "The Reclaimed Flame",
        "The Triumvirate",
        "Northern Concord",
        "The Commonwealth of orbis",
    ]
    away_names = [
        "Cult of Raccoon",
        "Registered Infra Offenders",
    ]

    t0 = time.time()
    batched_home = await q.resolve_alliance_names_batched(home_names)
    batched_away = await q.resolve_alliance_names_batched(away_names)
    home_ids = [int((batched_home.get(n) or {}).get('id')) for n in home_names if (batched_home.get(n) or {}).get('id')]
    away_ids = [int((batched_away.get(n) or {}).get('id')) for n in away_names if (batched_away.get(n) or {}).get('id')]
    print("Home IDs:", home_ids)
    print("Away IDs:", away_ids)

    from datetime import datetime, timedelta, timezone
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    t1 = time.time()
    wars = await q.get_wars_between_parties(home_ids, away_ids, cutoff_dt=cutoff, force_refresh=True)
    t2 = time.time()
    print("Wars:", len(wars or []), "time", round(t2 - t1, 2), "s")
    if wars:
        w = wars[0]
        print("Sample:", w.get('id'), w.get('att_alliance_id'), w.get('def_alliance_id'))
    print("Durations:", {"resolve": round(t1 - t0, 2), "wars": round(t2 - t1, 2)})


if __name__ == "__main__":
    asyncio.run(main())
