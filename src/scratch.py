from ortools.sat.python import cp_model

model = cp_model.CpModel()
x = model.NewIntVar(0, 10, 'x')
y = model.NewIntVar(0, 10, 'y')
model.Add(x + y == 10)
model.Add(x > y)

solver = cp_model.CpSolver()
status = solver.Solve(model)

if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
    print(f"x={solver.Value(x)}, y={solver.Value(y)}")
else:
    print("No solution found")