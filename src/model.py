import sys
sys.path.append("src/db")
from data_access import load_employees, load_availability, load_staffing_requirements
from ortools.sat.python import cp_model


# --- Problem setup ---

DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
LOCATIONS = ["Big Stand", "Marina"]

# 10 one-hour slots: 11am-12pm, 12-1pm, ... 8-9pm
HOURS = list(range(11, 21))  # represents the START hour of each 1-hr slot

# # Staffing requirements: (location, day) -> (min_needed, max_needed), applied to EVERY hour
# def get_staffing_requirement(location, day):
#     is_weekend = day in ("Sat", "Sun")
#     if location == "Big Stand":
#         return (8, 10) if is_weekend else (5, 5)
#     else:  # Marina
#         return (3, 3)

MAX_HOURS_PER_WEEK = 40

# --- Load real data from SQLite ---
_employees_raw = load_employees()  # list of (id, name, max_hours)
EMPLOYEES = [name for (_id, name, _max_hrs) in _employees_raw]
EMPLOYEE_MAX_HOURS = {name: max_hrs for (_id, name, max_hrs) in _employees_raw}

AVAILABILITY = load_availability()  # {name: {(day, hour), ...}}

_staffing = load_staffing_requirements()  # {(location, day): (min, max)}

def get_staffing_requirement(location, day):
    return _staffing[(location, day)]

# --- Build the CP-SAT model ---

model = cp_model.CpModel()

# Decision variable: assign[(employee, location, day, hour)] = 1 if working that hour
assign = {}
for e in EMPLOYEES:
    for loc in LOCATIONS:
        for d in DAYS:
            for h in HOURS:
                assign[(e, loc, d, h)] = model.NewBoolVar(f"assign_{e}_{loc}_{d}_{h}")

# Constraint: only assign employees to hours they're available for
for e in EMPLOYEES:
    for loc in LOCATIONS:
        for d in DAYS:
            for h in HOURS:
                if (d, h) not in AVAILABILITY[e]:
                    model.Add(assign[(e, loc, d, h)] == 0)

# Constraint: no employee works both locations in the same hour
for e in EMPLOYEES:
    for d in DAYS:
        for h in HOURS:
            model.Add(
                sum(assign[(e, loc, d, h)] for loc in LOCATIONS) <= 1
            )

# Constraint: staffing levels per location/day/hour
for loc in LOCATIONS:
    for d in DAYS:
        min_needed, max_needed = get_staffing_requirement(loc, d)
        for h in HOURS:
            total_assigned = sum(assign[(e, loc, d, h)] for e in EMPLOYEES)
            model.Add(total_assigned >= min_needed)
            model.Add(total_assigned <= max_needed)

# Constraint: max hours per week per employee (use per-employee cap from DB)
for e in EMPLOYEES:
    total_hours = sum(
        assign[(e, loc, d, h)]
        for loc in LOCATIONS for d in DAYS for h in HOURS
    )
    model.Add(total_hours <= EMPLOYEE_MAX_HOURS[e])

# Soft objective: reward longer shift blocks (4+ contiguous hours) and penalize short blocks by minimizing number of shift starts
working = {}

for e in EMPLOYEES:
    for d in DAYS:
        for h in HOURS:
            working[(e, d, h)] = model.NewBoolVar(f"working_{e}_{d}_{h}")
            model.Add(
                working[(e, d, h)] ==
                sum(assign[(e, loc, d, h)] for loc in LOCATIONS)
            )

starts = {}

for e in EMPLOYEES:
    for d in DAYS:
        for i, h in enumerate(HOURS):

            s = model.NewBoolVar(f"start_{e}_{d}_{h}")
            starts[(e,d,h)] = s

            if i == 0:
                model.Add(s == working[(e,d,h)])
            else:
                prev = HOURS[i-1]

                # start iff current=1 and previous=0
                model.Add(s >= working[(e,d,h)] - working[(e,d,prev)])
                model.Add(s <= working[(e,d,h)])
                model.Add(s <= 1 - working[(e,d,prev)])

short_shift_penalties = []

for e in EMPLOYEES:
    for d in DAYS:
        for i, h in enumerate(HOURS[:-3]):      # only hours with room for 4-hour block

            full4 = model.NewBoolVar(f"full4_{e}_{d}_{h}")

            window = [
                working[(e,d,HOURS[i+j])]
                for j in range(4)
            ]

            # full4 == AND(window)
            model.AddBoolAnd(window).OnlyEnforceIf(full4)
            model.AddBoolOr([w.Not() for w in window] + [full4])

            penalty = model.NewBoolVar(f"penalty_{e}_{d}_{h}")

            # penalty if a shift starts but doesn't last 4 hours
            model.Add(penalty >= starts[(e,d,h)] - full4)
            model.Add(penalty <= starts[(e,d,h)])
            model.Add(penalty <= 1 - full4)

            short_shift_penalties.append(penalty)

for e in EMPLOYEES:
    for d in DAYS:
        for h in HOURS[-3:]:
            short_shift_penalties.append(starts[(e,d,h)])

switches = [] # penalize switching between locations

for e in EMPLOYEES:
    for d in DAYS:
        for i in range(1, len(HOURS)):
            h0 = HOURS[i-1]
            h1 = HOURS[i]

            sw = model.NewBoolVar(f"switch_{e}_{d}_{h1}")

            # True iff Big -> Marina or Marina -> Big
            b0 = assign[(e, "Big Stand", d, h0)]
            b1 = assign[(e, "Big Stand", d, h1)]

            # Since there are only two locations and at most one assignment/hour,
            # a change in the Big Stand assignment indicates a location switch
            model.Add(sw >= b0 - b1)
            model.Add(sw >= b1 - b0)
            model.Add(sw <= b0 + b1)
            model.Add(sw <= 2 - b0 - b1)

            switches.append(sw)

# Soft objective: location preferences
preference_violations = []

for e in EMPLOYEES:
    preferred = LOCATION_PREFERENCE[e]

    for d in DAYS:
        for h in HOURS:
            for loc in LOCATIONS:
                if loc != preferred:
                    # This BoolVar is simply equal to being assigned
                    # to the non-preferred location.
                    violation = model.NewBoolVar(
                        f"pref_violation_{e}_{loc}_{d}_{h}"
                    )

                    model.Add(violation == assign[(e, loc, d, h)])

                    preference_violations.append(violation)

# Soft objective penalty minimization
model.Minimize(
    100 * sum(switches) +
    10 * sum(preference_violations) +
    sum(starts.values())
)

# Infeasibility diagnostics

def check_capacity():
    total_demand = 0
    for loc in LOCATIONS:
        for d in DAYS:
            min_needed, _ = get_staffing_requirement(loc, d)
            total_demand += min_needed * len(HOURS)

    for e in EMPLOYEES:
        total_supply = sum(
            assign[(e, loc, d, h)]
            for loc in LOCATIONS for d in DAYS for h in HOURS
        )

    print(f"Minimum hours demanded: {total_demand}")
    print(f"Maximum hours available: {total_supply}")
    if total_supply < total_demand:
        print(f"⚠️  Short by {total_demand - total_supply} hours — infeasible before solving.")
    else:
        print(f"✅  {total_supply - total_demand} hours of slack available.")


def check_slot_availability():
    problems = []
    for loc in LOCATIONS:
        for d in DAYS:
            min_needed, _ = get_staffing_requirement(loc, d)
            for h in HOURS:
                available_count = sum(
                    1 for e in EMPLOYEES if (d, h) in AVAILABILITY[e]
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


def diagnose_infeasibility():
    print("\n--- Running relaxed diagnostic (allows understaffing, minimizes it) ---\n")

    diag_model = cp_model.CpModel()

    diag_assign = {}
    for e in EMPLOYEES:
        for loc in LOCATIONS:
            for d in DAYS:
                for h in HOURS:
                    diag_assign[(e, loc, d, h)] = diag_model.NewBoolVar(f"d_{e}_{loc}_{d}_{h}")

    for e in EMPLOYEES:
        for loc in LOCATIONS:
            for d in DAYS:
                for h in HOURS:
                    if (d, h) not in AVAILABILITY[e]:
                        diag_model.Add(diag_assign[(e, loc, d, h)] == 0)

    for e in EMPLOYEES:
        for d in DAYS:
            for h in HOURS:
                diag_model.Add(sum(diag_assign[(e, loc, d, h)] for loc in LOCATIONS) <= 1)

    for e in EMPLOYEES:
        total_hours = sum(
            assign[(e, loc, d, h)]
            for loc in LOCATIONS for d in DAYS for h in HOURS
        )
        model.Add(total_hours <= EMPLOYEE_MAX_HOURS[e])

    deficits = {}
    for loc in LOCATIONS:
        for d in DAYS:
            min_needed, max_needed = get_staffing_requirement(loc, d)
            for h in HOURS:
                deficit = diag_model.NewIntVar(0, min_needed, f"deficit_{loc}_{d}_{h}")
                deficits[(loc, d, h)] = deficit
                total_assigned = sum(diag_assign[(e, loc, d, h)] for e in EMPLOYEES)
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

check_capacity()
solver = cp_model.CpSolver()
status = solver.Solve(model)

if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
    print("Schedule found:\n")
    for d in DAYS:
        print(f"=== {d} ===")

        violated_loc_pref = {}

        for loc in LOCATIONS:
            for h in HOURS:
                workers = [
                    e for e in EMPLOYEES
                    if solver.Value(assign[(e, loc, d, h)])
                ]
                print(f"  {loc} - {h}:00: {', '.join(workers) if workers else '(none)'}")

        # Check preference violations for this day
        for e in EMPLOYEES:
            preferred = LOCATION_PREFERENCE[e]

            for loc in LOCATIONS:
                if loc == preferred:
                    continue

                for h in HOURS:
                    if solver.Value(assign[(e, loc, d, h)]):
                        violated_loc_pref.setdefault(e, []).append(
                            f"{h}:00 ({loc})"
                        )
                violated = {}

            # Hours worked today at the non-preferred location
            hours = [
                h for h in HOURS
                if solver.Value(assign[(e, loc, d, h)])
            ]

            if not hours:
                continue

            # Break into contiguous ranges
            start = hours[0]
            prev = hours[0]

            for h in hours[1:] + [None]:
                if h is None or h != prev + 1:
                    violated.setdefault(e, []).append(
                        (loc, start, prev + 1)   # end is exclusive
                   )

                    if h is not None:
                        start = h

                if h is not None:
                    prev = h

    if violated:
        print("\nLocation preference violations:")

        for e in sorted(violated):
            print(f"  {e} (prefers {LOCATION_PREFERENCE[e]}):")

            for loc, start, end in violated[e]:
               print(f"      {start}:00–{end}:00 at {loc}")

        if violated_loc_pref:
            print("\nLocation preference violations:")
            for e, shifts in violated_loc_pref.items():
                print(f"  {e} prefers {LOCATION_PREFERENCE[e]}:")
                for s in shifts:
                    print(f"      {s}")

    print()
        
else:
    print("No feasible schedule found.\n")
    check_slot_availability()
    diagnose_infeasibility()
