#set page(paper: "a4", margin: (x: 2cm, y: 2cm))
#set text(font: "Liberation Sans", size: 11pt)
#set par(justify: true)

// Registration marks (corners)
#place(top + left, dx: 10mm, dy: 10mm, circle(radius: 2.5mm, fill: black))
#place(top + right, dx: -10mm, dy: 10mm, circle(radius: 2.5mm, fill: black))
#place(bottom + left, dx: 10mm, dy: -10mm, circle(radius: 2.5mm, fill: black))
#place(bottom + right, dx: -10mm, dy: -10mm, circle(radius: 2.5mm, fill: black))

#align(center)[
  #text(size: 16pt, weight: "bold")[Test Exam]
]

#grid(
  columns: (1fr, 1fr),
  gutter: 10mm,
  [*Student:* Student 9],
  [*ID:* `s009`],
)

#grid(
  columns: (1fr, 1fr),
  gutter: 10mm,
  [*Version:* `v1`],
  [*Date:* 2025-11-14],
)

#v(1em)

// Question 1
#block()[
  *1.* What design pattern ensures a class has only one instance? _(1 point)_

  #v(0.5em)
  #grid(
    columns: (8mm, 1fr),
    circle(radius: 3mm, stroke: 0.5pt) #text(weight: "bold")[A],
    [Singleton]
  )
]

#v(0.8em)

// Question 2
#block()[
  *2.* A binary tree where every node has either 0 or 2 children is called a full binary tree. _(1 point)_

  #v(0.5em)
  #grid(
    columns: (8mm, 1fr),
    circle(radius: 3mm, stroke: 0.5pt) #text(weight: "bold")[A],
    [True]
  )
  #grid(
    columns: (8mm, 1fr),
    circle(radius: 3mm, stroke: 0.5pt) #text(weight: "bold")[B],
    [False]
  )
]

#v(0.8em)

// Question 3
#block()[
  *3.* Which of the following is NOT a valid HTTP method? _(1 point)_

  #v(0.5em)
  #grid(
    columns: (8mm, 1fr),
    circle(radius: 3mm, stroke: 0.5pt) #text(weight: "bold")[A],
    [GET]
  )
  #grid(
    columns: (8mm, 1fr),
    circle(radius: 3mm, stroke: 0.5pt) #text(weight: "bold")[B],
    [POST]
  )
  #grid(
    columns: (8mm, 1fr),
    circle(radius: 3mm, stroke: 0.5pt) #text(weight: "bold")[C],
    [SEND]
  )
  #grid(
    columns: (8mm, 1fr),
    circle(radius: 3mm, stroke: 0.5pt) #text(weight: "bold")[D],
    [DELETE]
  )
]

#v(0.8em)

// Question 4
#block()[
  *4.* What does the acronym 'RAM' stand for? _(1 point)_

  #v(0.5em)
  #grid(
    columns: (8mm, 1fr),
    circle(radius: 3mm, stroke: 0.5pt) #text(weight: "bold")[A],
    [Random Access Memory]
  )
]

#v(0.8em)

// Question 5
#block()[
  *5.* What is the name of the sorting algorithm that repeatedly divides the array in half? _(1 point)_

  #v(0.5em)
  #grid(
    columns: (8mm, 1fr),
    circle(radius: 3mm, stroke: 0.5pt) #text(weight: "bold")[A],
    [Merge Sort]
  )
]

#v(0.8em)

// Question 6
#block()[
  *6.* What is the time complexity of binary search in a sorted array? _(1 point)_

  #v(0.5em)
  #grid(
    columns: (8mm, 1fr),
    circle(radius: 3mm, stroke: 0.5pt) #text(weight: "bold")[A],
    [O(log n)]
  )
  #grid(
    columns: (8mm, 1fr),
    circle(radius: 3mm, stroke: 0.5pt) #text(weight: "bold")[B],
    [O(n)]
  )
  #grid(
    columns: (8mm, 1fr),
    circle(radius: 3mm, stroke: 0.5pt) #text(weight: "bold")[C],
    [O(n log n)]
  )
  #grid(
    columns: (8mm, 1fr),
    circle(radius: 3mm, stroke: 0.5pt) #text(weight: "bold")[D],
    [O(n²)]
  )
]

#v(0.8em)

// Question 7
#block()[
  *7.* Which data structure uses LIFO (Last In First Out) principle? _(1 point)_

  #v(0.5em)
  #grid(
    columns: (8mm, 1fr),
    circle(radius: 3mm, stroke: 0.5pt) #text(weight: "bold")[A],
    [Queue]
  )
  #grid(
    columns: (8mm, 1fr),
    circle(radius: 3mm, stroke: 0.5pt) #text(weight: "bold")[B],
    [Stack]
  )
  #grid(
    columns: (8mm, 1fr),
    circle(radius: 3mm, stroke: 0.5pt) #text(weight: "bold")[C],
    [Linked List]
  )
  #grid(
    columns: (8mm, 1fr),
    circle(radius: 3mm, stroke: 0.5pt) #text(weight: "bold")[D],
    [Hash Table]
  )
]

#v(0.8em)

// Question 8
#block()[
  *8.* In object-oriented programming, what is encapsulation? _(1 point)_

  #v(0.5em)
  #grid(
    columns: (8mm, 1fr),
    circle(radius: 3mm, stroke: 0.5pt) #text(weight: "bold")[A],
    [Creating multiple instances of a class]
  )
  #grid(
    columns: (8mm, 1fr),
    circle(radius: 3mm, stroke: 0.5pt) #text(weight: "bold")[B],
    [Bundling data and methods that operate on that data]
  )
  #grid(
    columns: (8mm, 1fr),
    circle(radius: 3mm, stroke: 0.5pt) #text(weight: "bold")[C],
    [Inheriting properties from a parent class]
  )
  #grid(
    columns: (8mm, 1fr),
    circle(radius: 3mm, stroke: 0.5pt) #text(weight: "bold")[D],
    [Overriding methods in derived classes]
  )
]

#v(0.8em)
