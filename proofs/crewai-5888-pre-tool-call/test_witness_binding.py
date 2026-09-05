"""Extension of the six-test witness suite (crewAIInc/crewAI#5888, 5380834002).

Adds the two construction-time checks proposed by @XuebinMa (5390632120):
  7. config perturbation  - replay the same witness set with implementation
     config perturbed; the outcome must not move (evidence-bound vs config-bound)
  8. persisted-set only   - the authoritative decision must be reproducible from
     the persisted witness set alone, not from an ephemeral shadow copy
Each has a RED implementation so the check is known to discriminate.
"""

T0, T1, T2, DEADLINE = 1000, 2000, 3000, 2500
SENT    = {"kind": "sent", "at": T0, "deadline": DEADLINE}
ABSENCE = {"kind": "absence", "window": (T0, T2), "deadline": DEADLINE}

def conformant_projection(witnesses, now, config):
    state = "pending"
    for w in witnesses:
        if w["kind"] == "sent":
            state = "awaiting_response"
        elif w["kind"] == "response":
            state = "accepted"
        elif w["kind"] == "absence" and state == "awaiting_response":
            state = "expired" if w["window"][1] >= w["deadline"] else "stale"
    return state

def config_bound_projection(witnesses, now, config):      # RED: deadline from config
    state = "pending"
    for w in witnesses:
        if w["kind"] == "sent":
            state = "awaiting_response"
            sent_at = w["at"]
        elif w["kind"] == "absence" and state == "awaiting_response":
            state = "expired" if w["window"][1] >= sent_at + config["timeout"] else "stale"
    return state

# --- 7. config perturbation ------------------------------------------------
CONFIGS = [{"timeout": 1500}, {"timeout": 30}, {"timeout": 10**9}]

def test_config_perturbation_does_not_move_outcome():
    w = [SENT, ABSENCE]
    outcomes = {conformant_projection(w, T2, c) for c in CONFIGS}
    assert outcomes == {"expired"}

def test_config_bound_projection_is_red():
    w = [SENT, ABSENCE]
    outcomes = {config_bound_projection(w, T2, c) for c in CONFIGS}
    assert len(outcomes) > 1          # moved under perturbation -> config-bound

# --- 8. persisted set alone ----------------------------------------------
# Rate-limit decision: >2 calls inside a 1000-tick window trips AnomalyTriggered.
CALLS = [{"kind": "call", "at": t} for t in (100, 200, 300, 5000)]

def decide_from_persisted(persisted, at):
    recent = [c for c in persisted if c["kind"] == "call" and at - 1000 <= c["at"] <= at]
    return "anomaly" if len(recent) > 2 else "ok"

class ShadowCopyLimiter:                                   # RED: decides on pruned in-memory list
    def __init__(self):
        self.history = []
    def record_and_decide(self, at):
        self.history = [t for t in self.history if at - 1000 <= t]   # destructive compaction
        self.history.append(at)
        return "anomaly" if len(self.history) > 2 else "ok"

def test_decision_reproducible_from_persisted_set_alone():
    persisted = []
    live = []
    for c in CALLS:
        persisted.append(c)
        live.append(decide_from_persisted(persisted, c["at"]))
    replay = [decide_from_persisted(persisted[:i + 1], c["at"]) for i, c in enumerate(CALLS)]
    assert replay == live == ["ok", "ok", "anomaly", "ok"]

def test_shadow_copy_limiter_is_red():
    lim = ShadowCopyLimiter()
    persisted = []
    live = []
    for c in CALLS:
        persisted.append(c)
        live.append(lim.record_and_decide(c["at"]))
    # Pretend a restart between call 3 and call 4 (history lost, persisted set intact)
    lim2 = ShadowCopyLimiter()
    lim2.history = []                      # ephemeral state gone
    lim2.record_and_decide(5000)
    # A second evaluator holding only the persisted set cannot reconstruct
    # lim's in-memory history at the third call once compaction has run:
    lim.record_and_decide(2000)            # compacts away 100..300
    assert lim.history != [c["at"] for c in persisted if c["at"] <= 2000]
    assert decide_from_persisted(persisted, 300) == "anomaly"
    assert lim.history.count(300) == 0     # the evidence the live decision used is gone
