"""
Created on 8/1/21

Roomination script
Given csv of room preferences (single, double) and roommate preferences
generate a room assignment that maximizes collective happiness
while meeting the following constraints:
  - all people are assigned to exactly one room
  - all rooms have at least one person
  - all rooms do not have more than 2 people

@author: hoped
"""
from pulp import LpMaximize, LpProblem, LpStatus, lpSum, LpVariable
import csv

ROOMS_TO_EXCLUDE = {"The Drug"}  # GRA room 
SINGLE = " (single)"
DOUBLE = " (double)"

class Error(Exception):
    """Base class for exceptions in this module."""
    pass

class AssignmentError(Error):
    """Exception raised for errors in the input.

    Attributes:
        message -- explanation of the error
    """

    def __init__(self, message):
        self.message = message


class Person():
  def __init__(self, name, preferences):
    self.name = name
    self.preferences = preferences
    self.room = None
    self.roommate = None

  def set_roommate(self, assigned_roommate):
    '''
    assigneed_roommate -> Person object

    raises AssignmentError if person already has roommate
    '''
    if self.roommate:
      raise AssignmentError(f"{self.name} has roommate {self.roommate.name}. Cannot assign roommate {assigned_roommate.name}")
    
    self.roommate = assigned_roommate if assigned_roommate.name != self.name else None

  def set_room(self, assigned_room):
    '''
    assigned_room -> Room object

    raises AssignmentError if Person already has room
    '''
    if self.room:
      raise AssignmentError(f"{self.name} has room {self.room.name}. Cannot assign room {assigned_room.name}")
    
    self.room = assigned_room

  def get_happiness(self, room, roommate):
    '''
    room -> Room object
    roommate -> Person object

    assumes room names in survey csv were formatted like The Rainbow (single) or The Rainbow (double) 
    '''
    room_name = room.name+SINGLE if self == roommate else room.name+DOUBLE
    happiness = self.preferences[room_name] + self.preferences[roommate.name]
    return happiness

  def __str__(self):
    room = self.room.name if self.roommate else "no room"
    roomie = self.roommate.name if self.roommate else "single"
    return f"{self.name}: {room}, {roomie}"

  def __eq__(self, other_person):
    return isinstance(other_person, Person) and other_person.name == self.name

class Room():
  def __init__(self, name):
    self.name = name
    self.occupants = None # either None or list of 1 or 2 Person objects depending on if single or double

  def occupants_str(self):
    roomies = ""
    if self.occupants:
      for occupant in self.occupants:
        roomies += occupant.name + ", "
    return roomies

  def set_occupants(self, people):
    '''
    People -> list of length 2 containing two Person objects

    raises AssignmentError if room has occupants
    '''
    if self.occupants:
      raise AssignmentError(f"{self.name} has occupants {self.occupants_str()}. Cannot assign occupants {roomie.name for roomie in people}")
    
    if people[0] == people[1]:  # single
      self.occupants = [people[0]]
    else:  # double
      self.occupants = people

  def __str__(self):
    return f"{self.name}, {len(self.occupants)}, {self.occupants_str()}"

def assignment_happiness(room, person1, person2):
  happiness = person1.get_happiness(room, person2)
  if person1 != person2:
    happiness += person2.get_happiness(room, person1)
  return happiness

def read_file(survey_file):
  '''
  read in survey results from
  return: tuple<list<Rooms>, list<Person>> created from survey data
  '''
  rooms = []
  people = []
  people_names = set()
  room_names = {room_name for room_name in ROOMS_TO_EXCLUDE}
  f = open(survey_file, "r")

  lines = [line.replace("\n", "").split(",")[1:] for line in f]  # ignore first column (timestamp)
  f.close()
  all_names = lines[0][1:]  # ignore what is your name column, has people and room names
  all_responses = lines[1:]

  # Generate pikans and their preferences
  for response in all_responses:
    person_name = response[0]
    numeric_responses = response[1:]
    preferences = {name: int(number) if number else 1 for name, number in zip(all_names, numeric_responses)}
    people.append(Person(person_name, preferences))
    people_names.add(person_name)

  # Generate empty rooms
  for name in all_names:
    simple_name = name.replace(SINGLE, "").replace(DOUBLE, "") # remove (single) or (double) designation
    if simple_name not in room_names and name not in people_names:
      rooms.append(Room(simple_name))
      room_names.add(simple_name)

  return rooms, people

def make_assignments(rooms, people):
  room_dict = {room.name: room for room in rooms}
  people_dict = {pikan.name: pikan for pikan in people}
  people_combos = set()
  var_name_thing = {}  # map lp_variable_name to room or person objects

  # generate the happiness that would result from all possible room assignments
  happiness_dict = {} # {(room, pikan1, pikan2) : happiness of assignment}
  for k in range(len(rooms)):
    for i in range(len(people)):
      for j in range(i, len(people)): # no repeating roommate pairs
        name_tuple = rooms[k].name, people[i].name, people[j].name
        people_combos.add((people[i].name, people[j].name))
        happiness_dict[name_tuple] = assignment_happiness(rooms[k], people[i], people[j])

  # Create linear program maximization problem
  model = LpProblem(name="roomination", sense=LpMaximize)

  # initialize boolean decision variables
  var = {}
  for assignment in happiness_dict.keys():
    assignment_str = str(assignment).replace("(", "").replace(")","")
    var[assignment] = LpVariable(name=assignment_str, lowBound=0, cat="Binary")
    # Lp variable name alters assignment string, need to create mapping from var name to people / rooms
    # so that assignments can be made after problem is solved
    room, person1, person2 = var[assignment].name.split(",_")
    var_name_thing[room] = room_dict[assignment[0]]
    var_name_thing[person1] = people_dict[assignment[1]]
    var_name_thing[person2] = people_dict[assignment[2]]
  
  # create objective function --> maximize happiness
  obj_func =  lpSum([var[assignment]*happiness_dict[assignment] for assignment in var.keys()])
  model += obj_func


  # add constraints: each room assigned to exactly one pair of people
  for room in rooms:
    model += lpSum([var[(room.name,)+roomies] for roomies in people_combos]) == 1

  # add constraints: each person assigned to exactly one room
  for pikan in people:
    vars_with_pikan = []
    for assignment in var.keys():
      if pikan.name in assignment:
        vars_with_pikan.append(var[assignment])
    model += lpSum(vars_with_pikan) == 1

  result = model.solve()

  print(f"objective: {model.objective.value()}")

  # make assignments and check constraints based on results
  for variable in model.variables():
    if variable.value() == 1: # this assignment has been made
      room_name, person1_name, person2_name = variable.name.split(",_")
      room, person1, person2 = var_name_thing[room_name], var_name_thing[person1_name], var_name_thing[person2_name]
      room.set_occupants([person1, person2])
      person1.set_roommate(person2)
      if person1 != person2:
        person2.set_roommate(person1)

def create_csv(rooms, file_name):
  f = open(file_name, 'w', newline='')
  writer = csv.writer(f)
  column_names = ["Room", "# pikans", "pikan", "pikan"]
  writer.writerow(column_names)
  for room in rooms:
    writer.writerow(str(room).split(", "))
    print(room)
  f.close()

if __name__ == "__main__":
  rooms, people = read_file("survey.csv")  # must be in same directory
  make_assignments(rooms, people)

  # add forced assignments
  GRA_room = Room("The Drug")
  GRA_room.occupants = Person("Grant", {}), Person("Peyton", {})
  rooms.append(GRA_room)

  # create csv results
  create_csv(rooms, "roomination_results.csv")