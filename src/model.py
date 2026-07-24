import sys
sys.path.append("src/db")
from data_access import load_employees, load_availability, load_staffing_requirements, load_location_preferences, load_moppers
from ortools.sat.python import cp_model


# --- Problem setup (static, safe as module-level) ---

DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
LOCATIONS = ["Big Stand", "Marina"]
HOURS = list(range(11, 23))  # start hour of each 1-hr slot


def build_assign_vars(m, employees):
    a = {}
    for e in employees:
        for loc in LOCATIONS:
            for d in DAYS:
                for h in HOURS:
                    a[(e, loc, d, h)] = m.NewBoolVar(f"assign_{e}_{loc}_{d}_{h}")
    return a


def build_common_constraints(m, a, employees, availability, employee_max_hours):
    """Adds availability, no-double-booking, and hour-cap constraints to model m."""
    for e in employees:
        for loc in LOCATIONS:
            for d in DAYS:
                for h in HOURS:
                    if (d, h) not in availability[e]:
                        m.Add(a[(e, loc, d, h)] == 0)

    for e in employees:
        for d in DAYS:
            for h in HOURS:
                m.Add(sum(a[(e, loc, d, h)] for loc in LOCATIONS) <= 1)

    for e in employees:
        total_hours = sum(
            a[(e, loc, d, h)]
            for loc in LOCATIONS for d in DAYS for h in HOURS
        )
        m.Add(total_hours <= employee_max_hours[e])

    for e in employees:
        for d in DAYS:
            daily_hours = sum(
                a[(e, loc, d, h)]
                for loc in LOCATIONS for h in HOURS
            )
            m.Add(daily_hours <= 6)

def load_fresh_data():
    """Pulls current state from SQLite. Call this at the start of every solve/diagnostic."""
    employees_raw = load_employees()
    employees = [name for (_id, name, _max_hrs, _is_mopper) in employees_raw]
    employee_max_hours = {name: max_hrs for (_id, name, max_hrs, _is_mopper) in employees_raw}
    availability = load_availability()
    location_preferences = load_location_preferences()
    staffing = load_staffing_requirements()
    moppers = load_moppers()

    def get_staffing_requirement(location, day, hour):
        return staffing.get((location, day, hour), (0, 0))

    return {
        "employees": employees,
        "employee_max_hours": employee_max_hours,
        "availability": availability,
        "location_preferences": location_preferences,
        "get_staffing_requirement": get_staffing_requirement,
        "moppers": moppers,
    }


def build_main_model(data):
    """Builds the full model + objective. Returns (model, assign)."""
    employees = data["employees"]
    availability = data["availability"]
    employee_max_hours = data["employee_max_hours"]
    location_preferences = data["location_preferences"]
    get_staffing_requirement = data["get_staffing_requirement"]

    model = cp_model.CpModel()
    assign = build_assign_vars(model, employees)
    build_common_constraints(model, assign, employees, availability, employee_max_hours)

    # Staffing constraint
    for loc in LOCATIONS:
        for d in DAYS:
            for h in HOURS:
                min_needed = get_staffing_requirement(loc, d, h)
                total_assigned = sum(assign[(e, loc, d, h)] for e in employees)
                model.Add(total_assigned >= min_needed)

    # Hard constraint: at least one mopper must work the closing hour at Big Stand each day
    moppers = data["moppers"]
    closing_hour = HOURS[-1]
    mopper_list = [e for e in employees if e in moppers]

    if mopper_list:
        for d in DAYS:
            model.Add(
                sum(
                    assign[(e, "Big Stand", d, closing_hour)]
                    for e in mopper_list
                ) >= 1
            )

    # Soft objective: reward 4+ hour contiguous blocks, penalize short ones
    working = {}
    for e in employees:
        for d in DAYS:
            for h in HOURS:
                working[(e, d, h)] = model.NewBoolVar(f"working_{e}_{d}_{h}")
                model.Add(
                    working[(e, d, h)] ==
                    sum(assign[(e, loc, d, h)] for loc in LOCATIONS)
                )

    # Soft objective: minimize number of starts
    starts = {}
    for e in employees:
        for d in DAYS:
            for i, h in enumerate(HOURS):
                s = model.NewBoolVar(f"start_{e}_{d}_{h}")
                starts[(e, d, h)] = s
                if i == 0:
                    model.Add(s == working[(e, d, h)])
                else:
                    prev = HOURS[i - 1]
                    model.Add(s >= working[(e, d, h)] - working[(e, d, prev)])
                    model.Add(s <= working[(e, d, h)])
                    model.Add(s <= 1 - working[(e, d, prev)])

    short_shift_penalties = []
    for e in employees:
        for d in DAYS:
            for i, h in enumerate(HOURS[:-3]):
                full4 = model.NewBoolVar(f"full4_{e}_{d}_{h}")
                window = [working[(e, d, HOURS[i + j])] for j in range(4)]
                model.AddBoolAnd(window).OnlyEnforceIf(full4)
                model.AddBoolOr([w.Not() for w in window] + [full4])

                penalty = model.NewBoolVar(f"penalty_{e}_{d}_{h}")
                model.Add(penalty >= starts[(e, d, h)] - full4)
                model.Add(penalty <= starts[(e, d, h)])
                model.Add(penalty <= 1 - full4)
                short_shift_penalties.append(penalty)

    for e in employees:
        for d in DAYS:
            for h in HOURS[-3:]:
                short_shift_penalties.append(starts[(e, d, h)])

    # Soft objective: penalize switching locations within a day
    switches = []
    for e in employees:
        for d in DAYS:
            for i in range(1, len(HOURS)):
                h0 = HOURS[i - 1]
                h1 = HOURS[i]
                sw = model.NewBoolVar(f"switch_{e}_{d}_{h1}")
                b0 = assign[(e, "Big Stand", d, h0)]
                b1 = assign[(e, "Big Stand", d, h1)]
                model.Add(sw >= b0 - b1)
                model.Add(sw >= b1 - b0)
                model.Add(sw <= b0 + b1)
                model.Add(sw <= 2 - b0 - b1)
                switches.append(sw)

    # Soft objective: location preference penalty
    best_score = {}
    for e in employees:
        best_score[e] = max(
            location_preferences.get((e, loc), 0) for loc in LOCATIONS
        )

    preference_penalty_terms = []
    for e in employees:
        for loc in LOCATIONS:
            score = location_preferences.get((e, loc), 0)
            gap = best_score[e] - score
            if gap > 0:
                for d in DAYS:
                    for h in HOURS:
                        preference_penalty_terms.append(assign[(e, loc, d, h)] * gap)

    model.Minimize(
        100 * sum(switches) +
        10 * sum(preference_penalty_terms) +
        sum(starts.values())
    )

    return model, assign


# --- Infeasibility diagnostics ---

def check_capacity(data):
    employees = data["employees"]
    get_staffing_requirement = data["get_staffing_requirement"]
    employee_max_hours = data["employee_max_hours"]

    total_demand = 0
    for loc in LOCATIONS:
        for d in DAYS:
            for h in HOURS:
                min_needed = get_staffing_requirement(loc, d, h)
                total_demand += min_needed

    total_supply = sum(employee_max_hours[e] for e in employees)

    print(f"Minimum hours demanded: {total_demand}")
    print(f"Maximum hours available: {total_supply}")
    if total_supply < total_demand:
        print(f"⚠️  Short by {total_demand - total_supply} hours — infeasible before solving.")
    else:
        print(f"✅  {total_supply - total_demand} hours of slack available.")


def check_slot_availability(data):
    employees = data["employees"]
    availability = data["availability"]
    get_staffing_requirement = data["get_staffing_requirement"]

    problems = []
    for loc in LOCATIONS:
        for d in DAYS:
            for h in HOURS:
                min_needed = get_staffing_requirement(loc, d, h)
                available_count = sum(
                    1 for e in employees if (d, h) in availability[e]
                )
                if available_count < min_needed:
                    problems.append(
                        f"{loc} {d} {h}:00: needs {min_needed}, only {available_count} employees available"
                    )
    if problems:
        print("⚠️  Slot-level shortages found:")
        for p in problems:
            print(f"   - {p}")
    else:
        print("✅  Every slot individually has enough available employees.")
    return problems


def diagnose_infeasibility(data):
    print("\n--- Running relaxed diagnostic (allows understaffing, minimizes it) ---\n")

    employees = data["employees"]
    availability = data["availability"]
    employee_max_hours = data["employee_max_hours"]
    get_staffing_requirement = data["get_staffing_requirement"]

    diag_model = cp_model.CpModel()
    diag_assign = build_assign_vars(diag_model, employees)
    build_common_constraints(diag_model, diag_assign, employees, availability, employee_max_hours)

    deficits = {}
    for loc in LOCATIONS:
        for d in DAYS:
            for h in HOURS:
                min_needed = get_staffing_requirement(loc, d, h)
                max_needed = min_needed
                deficit = diag_model.NewIntVar(0, min_needed, f"deficit_{loc}_{d}_{h}")
                deficits[(loc, d, h)] = deficit
                total_assigned = sum(diag_assign[(e, loc, d, h)] for e in employees)
                diag_model.Add(total_assigned + deficit >= min_needed)
                diag_model.Add(total_assigned <= max_needed)

    diag_model.Minimize(sum(deficits.values()))

    diag_solver = cp_model.CpSolver()
    diag_status = diag_solver.Solve(diag_model)

    if diag_status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        total_deficit = diag_solver.ObjectiveValue()
        if total_deficit == 0:
            print("No deficits found — the original problem should actually be feasible. (Check for a bug.)")
        else:
            print(f"Best possible schedule is still understaffed by {int(total_deficit)} person-hours:\n")
            for (loc, d, h), var in deficits.items():
                val = diag_solver.Value(var)
                if val > 0:
                    label = "person" if val == 1 else "people"
                    print(f"   - {loc} {d} {h}:00: short by {val} {label}")
    else:
        print("Even the relaxed diagnostic model couldn't solve — something else may be wrong.")


# --- Solve ---

def solve_schedule():
    """Loads fresh data, builds a fresh model, solves it, and returns results
    including structured diagnostic data if infeasible."""
    data = load_fresh_data()
    employees = data["employees"]
    get_staffing_requirement = data["get_staffing_requirement"]
    availability = data["availability"]
    employee_max_hours = data["employee_max_hours"]

    # --- Capacity check ---
    total_demand = 0
    for loc in LOCATIONS:
        for d in DAYS:
            for h in HOURS:
                min_needed = get_staffing_requirement(loc, d, h)
                total_demand += min_needed

    total_supply = sum(employee_max_hours[e] for e in employees)
    capacity = {
        "total_demand": total_demand,
        "total_supply": total_supply,
        "shortfall": max(0, total_demand - total_supply),
        "slack": max(0, total_supply - total_demand),
    }

    model, assign = build_main_model(data)
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 10.0  # limit solve time
    solver.parameters.num_search_workers = 4  # use multiple threads
    status = solver.Solve(model)

    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        schedule = {d: {loc: {} for loc in LOCATIONS} for d in DAYS}
        for d in DAYS:
            for loc in LOCATIONS:
                for h in HOURS:
                    workers = [
                        e for e in employees
                        if solver.Value(assign[(e, loc, d, h)])
                    ]
                    schedule[d][loc][h] = workers
        return {"feasible": True, "schedule": schedule}

    # --- Infeasible: run diagnostics and return structured data ---

    # Slot-level availability check
    slot_shortages = []
    for loc in LOCATIONS:
        for d in DAYS:
            for h in HOURS:
                min_needed = get_staffing_requirement(loc, d, h)
                available_count = sum(
                    1 for e in employees if (d, h) in availability[e]
                )
                if available_count < min_needed:
                    slot_shortages.append({
                        "location": loc,
                        "day": d,
                        "hour": h,
                        "needed": min_needed,
                        "available": available_count,
                        "gap": min_needed - available_count,
                    })

    # Relaxed model: find minimum understaffing
    diag_model = cp_model.CpModel()
    diag_assign = build_assign_vars(diag_model, employees)
    build_common_constraints(
        diag_model, diag_assign, employees, availability, employee_max_hours
    )

    deficits = {}
    for loc in LOCATIONS:
        for d in DAYS:
            for h in HOURS:
                min_needed = get_staffing_requirement(loc, d, h)
                deficit = diag_model.NewIntVar(0, min_needed, f"deficit_{loc}_{d}_{h}")
                deficits[(loc, d, h)] = deficit
                total_assigned = sum(diag_assign[(e, loc, d, h)] for e in employees)
                diag_model.Add(total_assigned + deficit >= min_needed)

    diag_model.Minimize(sum(deficits.values()))
    diag_solver = cp_model.CpSolver()
    diag_solver.Solve(diag_model)

    deficit_slots = []
    total_deficit = int(diag_solver.ObjectiveValue())
    for (loc, d, h), var in deficits.items():
        val = diag_solver.Value(var)
        if val > 0:
            deficit_slots.append({
                "location": loc,
                "day": d,
                "hour": h,
                "shortage": val,
            })

    # Group deficit slots by (location, day) for cleaner display
    by_location_day = {}
    for slot in deficit_slots:
        key = (slot["location"], slot["day"])
        by_location_day.setdefault(key, []).append(slot)

    return {
        "feasible": False,
        "schedule": None,
        "diagnostics": {
            "capacity": capacity,
            "slot_shortages": slot_shortages,
            "total_deficit": total_deficit,
            "deficit_by_location_day": [
                {
                    "location": loc,
                    "day": d,
                    "slots": slots,
                    "total": sum(s["shortage"] for s in slots),
                }
                for (loc, d), slots in sorted(by_location_day.items())
            ],
        }
    }