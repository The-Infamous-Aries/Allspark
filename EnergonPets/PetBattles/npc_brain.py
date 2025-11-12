"""
Adaptive NPC Brain for Energon Pets battles.

Goals:
- Make strategic, human-like choices that adapt as health, charge, and party size change.
- Cover stages: Full, 3/4, 1/2, 1/4, >=10%, Critical.
- React to 1–4 opponents, their health, charging status, and eliminations.
- Occasionally take calculated risks and sometimes rely on luck.

Design notes:
- Uses stage baselines, risk assessment, pressure advantage, and party-aware heuristics.
- Avoids repetitive patterns while allowing momentum (attack after charge, etc.).
- Adds controlled randomness to feel less robotic without being erratic.
"""

from typing import Dict, Any, List
import random


class NPCBrain:
    """Adaptive, risk-aware NPC decision engine for monster actions."""

    def decide_action(self, monster_state: Dict[str, Any], players_state: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Decide monster action for the current round.

        Args:
            monster_state: Dict with keys:
                - hp: current monster HP
                - max_hp: max monster HP
                - charge_multiplier: current charge multiplier (1.0–16.0)
                - defending: whether monster is currently defending (resets after round in engine)
                - last_action: last action performed ("attack"|"defend"|"charge" or None)
                - seed: optional seed for reproducible randomness
                - prev_hp: optional previous round HP to compute loss rate
                - attack_stat: optional offensive stat for biasing choices
                - defense_stat: optional defensive stat for biasing choices
            players_state: List of dicts for each player with keys:
                - hp: current HP
                - max_hp: max HP
                - alive: bool
                - charging: bool

        Returns:
            Dict with:
                - action: "attack" | "defend" | "charge"
                - rationale: short text explaining the decision
                - strategy: targeting hint ("spread"|"focus_weakest"|"focus_strongest")
        """
        # Normalize inputs
        hp = max(0, int(monster_state.get("hp", 0)))
        max_hp = max(1, int(monster_state.get("max_hp", 1)))
        charge_mult = float(monster_state.get("charge_multiplier", 1.0))
        last_action = monster_state.get("last_action")
        defending = bool(monster_state.get("defending", False))
        seed = monster_state.get("seed")
        prev_hp = monster_state.get("prev_hp")
        attack_stat = float(monster_state.get("attack_stat", 1.0))
        defense_stat = float(monster_state.get("defense_stat", 1.0))

        # Controlled randomness: seed if provided
        if seed is not None:
            try:
                random.seed(int(seed))
            except Exception:
                # Ignore bad seeds; keep natural randomness
                pass

        # Compute percentages
        m_pct = (hp / max_hp) * 100.0
        loss_rate = 0.0
        if prev_hp is not None:
            try:
                prev_hp_i = max(0, int(prev_hp))
                loss_rate = max(0.0, (prev_hp_i - hp) / max_hp)
            except Exception:
                loss_rate = 0.0

        alive_players = [p for p in players_state if p.get("alive", False) and p.get("hp", 0) > 0]
        n_alive = len(alive_players)
        total_players = len(players_state)
        eliminations = max(0, total_players - n_alive)

        if n_alive == 0:
            # No opponents remain – default to defend to avoid odd behavior
            return {"action": "defend", "rationale": "No opponents alive", "strategy": "spread"}

        # Player health metrics
        player_pcts = [max(0.0, min(100.0, (p.get("hp", 0) / max(1, p.get("max_hp", 1))) * 100.0)) for p in alive_players]
        avg_player_pct = sum(player_pcts) / len(player_pcts)
        weakest_pct = min(player_pcts)
        strongest_pct = max(player_pcts)
        any_player_critical = weakest_pct <= 10.0
        any_player_finisher_range = weakest_pct <= 25.0
        players_charging = [p for p in alive_players if p.get("charging", False)]
        charging_count = len(players_charging)
        many_players = n_alive >= 3

        # Determine stage buckets with explicit >=10% band
        if hp == max_hp:
            stage = "full"
        elif m_pct >= 75.0:
            stage = "three_quarters"
        elif m_pct >= 50.0:
            stage = "half"
        elif m_pct >= 25.0:
            stage = "quarter"
        elif m_pct >= 10.0:
            stage = "ten_percent"
        else:
            stage = "critical"

        # Baseline weights per stage (human-leaning tendencies)
        weights = {"attack": 0, "defend": 0, "charge": 0}
        strategy = "spread"

        if stage == "full":
            # Open assertively; build charge against larger parties
            weights["attack"] = 6
            weights["defend"] = 1
            weights["charge"] = 3 if many_players else 2
        elif stage == "three_quarters":
            # Keep pressure; moderate defense if needed
            weights["attack"] = 6
            weights["defend"] = 2
            weights["charge"] = 3 if many_players else 2
        elif stage == "half":
            # Balanced; threaten with charge when safe
            weights["attack"] = 5
            weights["defend"] = 3
            weights["charge"] = 2
        elif stage == "quarter":
            # 49%–15%: mostly attack/defend; charge decays with health and loss rate
            weights["attack"] = 5
            weights["defend"] = 5
            # Base small charge that decays as HP drops
            charge_base = 2
            charge_decay = int(max(0, (50.0 - m_pct) / 12.0))  # stronger decay toward 25%
            weights["charge"] = max(0, charge_base - charge_decay)
            # Penalize charge further if taking damage quickly
            if loss_rate >= 0.20:
                weights["charge"] = max(0, weights["charge"] - 2)
                weights["defend"] += 1
        elif stage == "ten_percent":
            # 15%–24%: only attack or defend; no charging
            weights["attack"] = 4
            weights["defend"] = 6
            weights["charge"] = 0
        else:  # critical (<10%)
            # Turtle hard unless a finishing window appears
            weights["attack"] = 2
            weights["defend"] = 7
            weights["charge"] = 0

        # Party-size adjustments
        if n_alive == 1:
            # One pet: exploit openings and finish quickly
            weights["attack"] += 2
            if weights["defend"] > 0:
                weights["defend"] -= 1
        elif n_alive == 2:
            # Two pets: balanced pressure
            weights["attack"] += 1
        elif n_alive == 4:
            # Four pets: value scaling via charge early/mid
            if stage in ("full", "three_quarters", "half"):
                weights["charge"] += 1

        # Exploit vulnerable targets
        if any_player_finisher_range:
            weights["attack"] += 2
            strategy = "focus_weakest"
        elif avg_player_pct < 50.0 and not many_players:
            weights["attack"] += 1

        # Pressure advantage: compare monster vs party health
        pressure_advantage = m_pct - avg_player_pct
        if pressure_advantage >= 15:
            # Ahead: be bolder
            weights["attack"] += 2
            if stage in ("full", "three_quarters") and many_players:
                weights["charge"] += 1
        elif pressure_advantage <= -15:
            # Behind: play safer
            weights["defend"] += 2
            weights["charge"] = max(0, weights["charge"] - 1)

        # Charging context
        safe_to_charge = (
            stage in ("full", "three_quarters", "half") and
            avg_player_pct >= 50.0 and
            not any_player_critical and
            charging_count == 0
        )
        if not safe_to_charge:
            weights["charge"] = max(0, weights["charge"] - 2)

        # Cash in when already charged
        if charge_mult >= 4.0:
            weights["attack"] += 2
            weights["charge"] = max(0, weights["charge"] - 2)
            # If surrounded and healthy, consider focusing strongest to break threat
            if many_players and m_pct >= 50.0 and not any_player_finisher_range:
                strategy = "focus_strongest"

        # React to players charging (threat management)
        if charging_count >= 2 and m_pct <= 50.0:
            # Expect big hits; defend more
            weights["defend"] += 2
            weights["charge"] = 0
        elif charging_count == 1 and stage in ("full", "three_quarters", "half"):
            # Counter-pressure rather than turtling
            weights["attack"] += 1
            strategy = "focus_strongest" if strongest_pct >= 60.0 else strategy

        # Momentum and anti-looping behavior
        if last_action == "charge":
            # After charging, prefer to attack unless extremely unsafe
            weights["attack"] += 2
            if stage in ("quarter", "critical"):
                weights["defend"] += 1
            weights["charge"] = max(0, weights["charge"] - 2)
        elif last_action == "defend":
            # Don't turtle indefinitely
            weights["attack"] += 1
        elif last_action == "attack" and stage in ("quarter", "ten_percent", "critical"):
            # Avoid reckless repeat attacks when very low
            weights["defend"] += 1

        # Elimination momentum: fewer enemies -> more aggression
        if eliminations >= 1 and m_pct >= 25.0:
            weights["attack"] += 1

        # Stat-based bias: ATT vs DEF should strongly influence A/D, especially below 50%
        bias_den = max(1.0, attack_stat + defense_stat)
        attack_bias = (attack_stat - defense_stat) / bias_den  # [-1, 1]
        bias_scale = 2 if m_pct <= 50.0 else 1
        if attack_bias > 0:
            weights["attack"] += 1 + int(round(abs(attack_bias) * 3)) * bias_scale
        elif attack_bias < 0:
            weights["defend"] += 1 + int(round(abs(attack_bias) * 3)) * bias_scale

        # Early-band charge synergy: when stats are balanced, charge boosts both A/D
        if m_pct >= 50.0 and abs(attack_bias) < 0.15 and charge_mult < 4.0:
            weights["charge"] += 1

        # 15%–Death: ensure only attack/defend
        if m_pct <= 15.0:
            weights["charge"] = 0
            # Bias becomes very strong at the brink
            if attack_bias > 0:
                weights["attack"] += 2
            elif attack_bias < 0:
                weights["defend"] += 2

        # Risk profile: higher early, lower at critical; add slight noise
        base_risk = {
            "full": 0.7,
            "three_quarters": 0.65,
            "half": 0.55,
            "quarter": 0.4,
            "ten_percent": 0.3,
            "critical": 0.25,
        }[stage]
        # Advantage raises risk; disadvantage lowers risk
        adv_factor = max(-0.2, min(0.2, pressure_advantage / 100.0))
        risk = max(0.05, min(0.95, base_risk + adv_factor + (random.random() - 0.5) * 0.1))

        # Luck: rare swings to feel human
        luck_roll = random.random()
        if luck_roll < 0.08:
            # 8%: take a bold or odd choice
            if stage in ("full", "three_quarters") and weights["charge"] > 0:
                weights["charge"] += 2
            else:
                # Flip between attack and defend slightly
                if pressure_advantage >= 0:
                    weights["attack"] += 1
                else:
                    weights["defend"] += 1

        # Clamp to non-negative
        for k in weights:
            weights[k] = max(0, weights[k])

        total = weights["attack"] + weights["defend"] + weights["charge"]
        if total <= 0:
            return {"action": "attack", "rationale": "Fallback decision", "strategy": strategy}

        # Blend randomness with weights for human-like variability
        # Add small stochastic noise proportional to risk
        noisy: Dict[str, float] = {}
        for k, w in weights.items():
            if k == "charge" and m_pct <= 15.0:
                # Below or equal to 15% HP, never allow charge even with noise.
                noisy[k] = 0.0
            else:
                noisy[k] = max(0.0, w + risk * random.uniform(0, 1.0))

        # Choose action via weighted sampling; deterministic tie-breakers when near equal
        # Compute top weights
        top = max(noisy.values())
        candidates = [k for k, v in noisy.items() if abs(v - top) < 0.75]
        if len(candidates) == 1:
            action = candidates[0]
        else:
            # Prefer attack > defend > charge when close
            for pref in ("attack", "defend", "charge"):
                if pref in candidates:
                    action = pref
                    break
            else:
                action = random.choices(list(noisy.keys()), weights=list(noisy.values()))[0]

        # Strategy refinement
        if any_player_finisher_range:
            strategy = "focus_weakest"
        elif charging_count >= 1 and m_pct >= 50.0 and not any_player_finisher_range:
            strategy = "focus_strongest"
        elif many_players and stage in ("full", "three_quarters") and action == "attack":
            strategy = "spread"

        rationale = (
            f"stage={stage}, n_alive={n_alive}, avg_player_pct={avg_player_pct:.0f}, "
            f"weakest_pct={weakest_pct:.0f}, strongest_pct={strongest_pct:.0f}, "
            f"charge_mult=x{charge_mult:.1f}, charging_count={charging_count}, risk={risk:.2f}, "
            f"att={attack_stat:.1f}, def={defense_stat:.1f}, bias={attack_bias:.2f}, loss_rate={loss_rate:.2f}"
        )

        return {"action": action, "rationale": rationale, "strategy": strategy}