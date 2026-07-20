from ortools.sat.python import cp_model

# --- Problem setup ---

DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
SHIFTS = ["lunch", "dinner"]  # lunch = 11am-5pm (6hrs), dinner = 5pm-9pm (4hrs)
LOCATIONS = ["Big Stand", "Marina"]

SHIFT_HOURS = {"lunch": 6, "dinner": 4}

# Staffing requirements: (location, day, shift) -> (min_needed, max_needed)
def get_staffing_requirement(location, day):
    is_weekend = day in ("Sat", "Sun")
    if location == "Big Stand":
        return (8, 10) if is_weekend else (5, 5)
    else:  # Marina
        return (3, 3)

MAX_HOURS_PER_WEEK = 40

# --- Placeholder employees ---
# availability[employee] = set of (day, shift) they CAN work

EMPLOYEES = ["Alice", "Ben", "Carla", "Dan", "Elena", "Frank", "Gina", "Hank",
             "Ivy", "Jack", "Kim", "Leo", "Mia", "Noah",
             "Oscar", "Piper", "Quinn", "Ruby"]

AVAILABILITY = {
    "Alice":  {(d, s) for d in DAYS for s in SHIFTS},
    "Ben":    {(d, s) for d in ["Mon","Tue","Wed","Thu","Fri"] for s in SHIFTS},
    "Carla":  {(d, s) for d in DAYS for s in SHIFTS},
    "Dan":    {(d, s) for d in DAYS for s in SHIFTS},
    "Elena":  {(d, s) for d in DAYS for s in SHIFTS} - {("Fri","dinner"), ("Sat","dinner")},
    "Frank":  {(d, s) for d in DAYS for s in SHIFTS},
    "Gina":   {(d, s) for d in DAYS for s in SHIFTS},
    "Hank":   {(d, s) for d in DAYS for s in SHIFTS},
    "Ivy":    {(d, s) for d in DAYS for s in SHIFTS},
    "Jack":   {(d, s) for d in DAYS for s in SHIFTS},
    "Kim":    {(d, s) for d in ["Sat","Sun"] for s in SHIFTS},
    "Leo":    {(d, s) for d in ["Sat","Sun"] for s in SHIFTS},
    "Mia":    {(d, s) for d in DAYS for s in SHIFTS},
    "Noah":   {(d, s) for d in DAYS for s in SHIFTS},
    "Oscar":  {(d, s) for d in DAYS for s in SHIFTS},
    "Piper":  {(d, s) for d in DAYS for s in SHIFTS},
    "Quinn":  {(d, s) for d in DAYS for s in SHIFTS},
    "Ruby":   {(d, s) for d in DAYS for s in SHIFTS},
}

# --- Build the CP-SAT model ---

model = cp_model.CpModel()

# Decision variable: assign[(employee, location, day, shift)] = 1 if that
# employee works that location/day/shift, else 0.
assign = {}
for e in EMPLOYEES:
    for loc in LOCATIONS:
        for d in DAYS:
            for s in SHIFTS:
                assign[(e, loc, d, s)] = model.NewBoolVar(f"assign_{e}_{loc}_{d}_{s}")

# Constraint: only assign employees to slots they're available for
for e in EMPLOYEES:
    for loc in LOCATIONS:
        for d in DAYS:
            for s in SHIFTS:
                if (d, s) not in AVAILABILITY[e]:
                    model.Add(assign[(e, loc, d, s)] == 0)

# Constraint: no employee works both locations in the same day/shift
for e in EMPLOYEES:
    for d in DAYS:
        for s in SHIFTS:
            model.Add(
                sum(assign[(e, loc, d, s)] for loc in LOCATIONS) <= 1
            )

# Constraint: staffing levels per location/day/shift
for loc in LOCATIONS:
    for d in DAYS:
        min_needed, max_needed = get_staffing_requirement(loc, d)
        for s in SHIFTS:
            total_assigned = sum(assign[(e, loc, d, s)] for e in EMPLOYEES)
            model.Add(total_assigned >= min_needed)
            model.Add(total_assigned <= max_needed)

# Constraint: max hours per week per employee
for e in EMPLOYEES:
    total_hours = sum(
        assign[(e, loc, d, s)] * SHIFT_HOURS[s]
        for loc in LOCATIONS for d in DAYS for s in SHIFTS
    )
    model.Add(total_hours <= MAX_HOURS_PER_WEEK)

def check_capacity():
    total_demand = 0
    for loc in LOCATIONS:
        for d in DAYS:
            min_needed, _ = get_staffing_requirement(loc, d)
            for s in SHIFTS:
                total_demand += min_needed * SHIFT_HOURS[s]

    total_supply = len(EMPLOYEES) * MAX_HOURS_PER_WEEK

    print(f"Minimum hours demanded: {total_demand}")
    print(f"Maximum hours available: {total_supply}")
    if total_supply < total_demand:
        print(f"⚠️  Short by {total_demand - total_supply} hours — infeasible before solving.")
    else:
        print(f"✅  {total_supply - total_demand} hours of slack available.")

# --- Solve ---

check_capacity()
solver = cp_model.CpSolver()
status = solver.Solve(model)

if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
    print("Schedule found:\n")
    for d in DAYS:
        print(f"=== {d} ===")
        for loc in LOCATIONS:
            for s in SHIFTS:
                workers = [e for e in EMPLOYEES if solver.Value(assign[(e, loc, d, s)])]
                print(f"  {loc} - {s}: {', '.join(workers) if workers else '(none)'}")
        print()
else:
    print("No feasible schedule found.")