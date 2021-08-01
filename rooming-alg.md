# This file defines and explains the starting point for rooming people into
# double rooms and single rooms, based on both (lack of) roommate preference
# and room choice preference. Please read on carefully for instructions on how
# to participate in determining the initial configuration.
set people; set rooms; var utility{i in people};

# Each person should describe their preferences using the three parameters below.
# All parameters are on the same scale in the sense that a room swap that would
# increase one of the parameters and decrease another by the same amount is
# considered irrelevant to you. No "scaling" or "normalization" is performed.  
# An input of 0 corresponds to having no desire for that option. An input of 100
# corresponds to having a strong desire for that option. 


# 1. roommate preference (0..100), for every person (yourself=single)
param pref_mate {i in people, j in people}, >= 0, <= 100;
# 2. room preference (0..100), given it is a single, for each room
param pref_single{i in people, k in rooms}, >= 0, <= 100;
# 3. room preference (0..100), given it is a double, for each room
param pref_double{i in people, k in rooms}, >= 0, <= 100;

# The solution x (a 3D boolean array) will describe the initial rooming
# configuration: x[i,j,k] = 1 iff people i and j are in room k.
var x{i in people, j in people, k in rooms}, binary;

# The algorithm will maximize the total (summed) utility of all people.
maximize total : sum{i in people} utility[i];
# Each person's utility is in turn made up as the sum of two values: the
# preference for the roommate, and the preference for the room they are placed
# in (based on whether there is somebody else in that room).
s.t. utility_eq{i in people}: utility[i] =
  sum{j in people, k in rooms}               # only one addend is nonzero b/c
    x[i,j,k] * (                             # each person is in exactly 1 room
      if i == j                              # rooming with yourself -> single
      then pref_mate[i,i] + pref_single[i,k]
      else pref_mate[i,j] + pref_double[i,k]
    );

# Since 10 units of one person's utility is considered interchangable with
# another person's 10 units of utility, it is in your interest to use the full
# 0..100 range when indicating your preferences. If you prefer having a room
# for yourself, you can indicate it by ranking yourself higher than other
# people in the roommate preference list. You are encouraged to express all
# preferences you have in the algorithm inputs, even if you think you will (or
# even should) be asked to compromise on them during roomination. Unfortunately,
# it is not possible to condition room preference on roommate preference here.
# Keep in mind that the room (not roommate) preferences are published.

# Of course, we will need to actually encode the constraints; here goes:
s.t. has_room{i in people}: sum{j in people, k in rooms} x[i,j,k] = 1;
s.t. used_once{k in rooms}: sum{i in people, j in people : i<=j} x[i,j,k] <= 1;
s.t. symmetry{i in people, j in people, k in rooms : i<j}: x[i,j,k] = x[j,i,k];

solve;

printf "\nNON-PUBLIC utilities:\n\n";
for {i in people}
    printf "%s: %f\n", i, utility[i];

printf "\nPUBLIC assignments:\n";
for {k in rooms}
    for {i in people}
        for {j in people : i<=j}
            printf "%s",
                if x[i,j,k] then
                    if i != j then k & ": " & i & ", " & j & ";"
                    else k & ": " & i & ";"
                else "";
printf "\n";

# Andres Erbsen <andreser@mit.edu>, Nov 2015, MIT License. In GNU MathProg.