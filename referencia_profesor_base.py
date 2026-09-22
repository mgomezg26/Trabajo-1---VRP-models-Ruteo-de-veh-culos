import math
import numpy as np
import matplotlib.pyplot as plt
import gurobipy as gp
from gurobipy import GRB
import random

"""
================================================================================
Vehicle Routing Problem (VRP) with Capacity and Time Window Constraints
================================================================================

PROBLEM DESCRIPTION:
- Depot-based vehicle routing with multiple vehicles
- Each customer has a demand that must be satisfied
- Each vehicle has a maximum capacity constraint
- Objective: Minimize the makespan (maximum route completion time)
- Constraints: Single visit per customer, capacity limits, time limits, subtour elimination

MATHEMATICAL FORMULATION:
- X[i,j]: Binary variable indicating if arc (i,j) is traversed
- t[i]: Continuous variable for arrival time at node i
- w[i,j]: Flow variable for subtour elimination (Miller-Tucker-Zemlin formulation)
- L[i,j]: Flow variable for load tracking across arc (i,j)
- Rmax: Continuous variable representing the maximum route completion time (objective)

SOLUTION APPROACH:
- Mixed Integer Programming (MIP) solved with Gurobi optimizer
- Big-M constraints for temporal continuity
- MTZ formulation to prevent subtours
- Flow conservation for load feasibility
"""

# ============================================================================
# DATA LOADING AND PREPROCESSING
# ============================================================================

# Load instance from file (TSP format: coordinate index columns)
filename = 'ch150.tsp'

# Read node coordinates from file
coord = np.loadtxt(filename)
n = len(coord)
n = 20  # For testing, limit to 20 nodes

# Initialize distance matrix and coordinate lists
dist = []  # 2D list: dist[i][j] = Euclidean distance from node i to node j
x = []     # x-coordinates of all nodes
y = []     # y-coordinates of all nodes
for i in range(n):
    dist.append([])
    x.append(coord[i][0])
    y.append(coord[i][1])
    # Compute pairwise Euclidean distances
    for j in range(n):
        dist[i].append(math.sqrt((coord[i][0] - coord[j][0])**2 + (coord[i][1] - coord[j][1])**2))

# plt.plot(x, y, 'o')
# plt.show()

# ============================================================================
# INSTANCE PARAMETERS
# ============================================================================

# Generate random demand for each customer (node 1 to n-1)
# Demand at depot (node 0) is implicitly zero
q = [random.randint(1, 10) for _ in range(n)]

# Vehicle capacity constraint
Q = 20

# Number of vehicles
K = 6

# ============================================================================
# MATHEMATICAL MODEL: DECISION VARIABLES
# ============================================================================

md = gp.Model("VRP base")

# Binary decision variables for arc traversal
# X[i,j] = 1 if and only if arc (i,j) is used in the optimal solution
# Comment: These form the backbone of the routing structure
X = md.addVars(n, n, vtype=GRB.BINARY, name='X')

# Continuous variables for arrival time at each node
# t[i] represents the time (e.g., minutes) when node i is visited
# Lower bound = 0 ensures non-negative times
t = md.addVars(n, vtype=GRB.CONTINUOUS, name='t', lb=0)

# Continuous flow variables for subtour elimination (Miller-Tucker-Zemlin)
# w[i,j] tracks the sequential order of node visits within a route
# Purpose: Prevent disconnected loops (subtours) without using exponentially many constraints
w = md.addVars(n, n, vtype=GRB.CONTINUOUS, name='w')

# Continuous flow variables for load tracking
# L[i,j] represents the cumulative load being transported on arc (i,j)
# Purpose: Enforce capacity constraints and demand satisfaction per customer
L = md.addVars(n, n, vtype=GRB.CONTINUOUS, name='L')

# Makespan variable: the time when the last vehicle returns to depot
# This is the primary objective to minimize
Rmax = md.addVar(vtype=GRB.CONTINUOUS, name='Rmax')

# ============================================================================
# SET DEFINITIONS
# ============================================================================

# Set of all nodes (0 = depot, 1..n-1 = customers)
V = range(n)

# Set of customer nodes only (excludes depot)
Vp = range(1, n)

# Big-M constant for constraint relaxation
# Used in temporal continuity constraints to disable them when X[i,j] = 0
# Heuristic: max distance * number of nodes (conservative upper bound on any route)
M = max([dist[i][j] for i in V for j in V if i != j]) * n

# ============================================================================
# CONSTRAINTS
# ============================================================================

# CONSTRAINT 1: Each customer must be visited exactly once
# Ensures single visit per customer (degree constraint for incoming arcs)
# Rationale: Each customer j must have exactly one predecessor in the routing plan
md.addConstrs(gp.quicksum(X[i, j]  for i in V if i != j) == 1  for j in Vp)

# CONSTRAINT 2: Flow conservation at each node
# For each node, the number of incoming arcs equals the number of outgoing arcs
# Rationale: Ensures route continuity (if vehicle arrives, it must depart)
md.addConstrs(gp.quicksum(X[i, j] - X[j, i]  for i in V) == 0  for j in V)

# CONSTRAINT 3: No self-loops
# Prevents a vehicle from "traveling" from a node to itself
md.addConstr(gp.quicksum(X[i, i]  for i in V) == 0)

# CONSTRAINT 4: Maximum number of active vehicles
# Limits departures from depot to at most K routes
# Rationale: Restricts the number of simultaneous vehicles in operation
md.addConstr(gp.quicksum(X[0, i]  for i in Vp) <= K)

# CONSTRAINT 5: Temporal continuity using Big-M formulation
# If arc (i,j) is traversed, then t[j] >= t[i] + d[i][j]
# If arc (i,j) is NOT traversed, the constraint is relaxed (M term becomes inactive)
# Rationale: Ensures travel time is accounted for in arrival times
md.addConstrs(t[j] >= t[i] + dist[i][j] - M * (1 - X[i, j])  for j in Vp  for i in V  if i != j)

# CONSTRAINT 6: Depot starts at time zero
# Anchor constraint: operations begin at the depot
md.addConstr(t[0] == 0)

# CONSTRAINT 7: Time limit for route completion
# Each customer j must be visited and return to depot within T_max time units
# Rationale: Enforces service time window (e.g., end-of-day deadline)
T_max = 1600
md.addConstrs(t[j] + dist[j][0] <= T_max  for j in Vp)

# CONSTRAINT 8: Miller-Tucker-Zemlin (MTZ) upper bound on order variables
# Ensures w[i,j] is only non-zero if arc (i,j) is actually used
md.addConstrs(w[i, j] <= n * X[i, j]  for i in V  for j in V)

# CONSTRAINT 9: MTZ flow conservation for subtour elimination
# Ensures a consistent numbering of nodes in each route, preventing disconnected cycles
# If a subtour exists (not connected to depot), the flow balance will be violated
md.addConstrs(gp.quicksum(w[i, j] - w[j, i]  for i in V) == 1  for j in Vp)

# CONSTRAINT 10: Load capacity upper bound on arcs
# Ensures L[i,j] can only be non-zero if the arc is traversed
md.addConstrs(L[i, j] <= Q * X[i, j]  for i in V  for j in V)

# CONSTRAINT 11: Load conservation at customer nodes
# The demand q[j] at customer j must be satisfied
# Load balance: incoming load - outgoing load = customer demand
# Rationale: Ensures each customer receives exactly their required quantity
md.addConstrs(gp.quicksum(L[i, j] - L[j, i]  for i in V) == q[j]  for j in Vp)

# CONSTRAINT 12: Makespan definition
# The makespan must be at least as large as the completion time of any route
# Completion time = arrival time at customer j + return distance to depot
md.addConstrs(Rmax >= t[j] + dist[j][0]  for j in Vp)

# ============================================================================
# OBJECTIVE FUNCTION
# ============================================================================

# Objective 1: Minimize total distance (commented out)
# obj_distance = gp.quicksum(dist[i][j] * X[i, j] for j in V for i in V)
# md.setObjective(obj_distance, GRB.MINIMIZE)

# Objective 2: Minimize makespan (maximum route completion time) [ACTIVE]
# Rationale: Optimizes for temporal efficiency, useful for same-day delivery scenarios
md.setObjective(Rmax, GRB.MINIMIZE)

# ============================================================================
# MODEL UPDATE AND OPTIMIZATION
# ============================================================================

# Update model to reflect all variables and constraints
md.update()

# Configure Gurobi solver parameters
md.setParam(GRB.Param.OutputFlag, 1)  # Display solver progress
md.setParam(GRB.Param.TimeLimit, 3600)  # Set time limit in seconds

# Solve the MIP
md.optimize()

# ============================================================================
# SOLUTION EXTRACTION AND DISPLAY
# ============================================================================

# Extract and print the routing decisions (which arcs are used)
print("\n" + "="*60)
print("OPTIMAL ROUTING SOLUTION")
print("="*60)

for i in range(n):
    for j in range(n):
        # Print arc if it has a non-negligible value (> 0.5 due to binary nature)
        if X[i, j].X > 0.5:
            print(f'Arc X[{i},{j}] = {X[i, j].X:.1f} | Distance: {dist[i][j]:.2f}')

# Optional: Print arrival times and loads
print("\n" + "="*60)
print("ARRIVAL TIMES AND LOADS")
print("="*60)

for j in Vp:
    if t[j].X is not None:
        print(f'Node {j}: Arrival Time = {t[j].X:.2f}')