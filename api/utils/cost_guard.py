import os

# Maximum allowed cost in EUR for a single job
MAX_COST = float(os.getenv("QD_COST_GUARD_EUR", "150"))


def estimate_job_cost(profile: dict) -> float:
    """
    Extremely simple placeholder cost model.
    You can replace this with actual GPU/CPU/time estimation.
    """
    minutes = float(profile.get("minutes", 10))
    res = profile.get("res", "2K")

    # simple multiplier
    res_factor = 1.0 if res == "2K" else 2.0

    return 0.02 * minutes * res_factor


def allowed(profile: dict) -> bool:
    """
    Returns False if job is too expensive to run.
    """
    return estimate_job_cost(profile) <= MAX_COST
