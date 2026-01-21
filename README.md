# AI Car Racing Game (Pygame)

This project is based on the following repository:  
https://github.com/eugene-ats/Pygame-Car-Racing/tree/main

## Learning Resources

Currently following video tutorials:  
https://youtu.be/V_B5ZCli-rA?si=h6fmWZTDtIat0Kqe

## Project Idea

The goal of this project is to build a **car racing game** where each car uses a different **pathfinding or AI algorithm** to navigate the track.

Some algorithms will perform well, others poorly, and part of the learning experience is understanding *why*.

In addition to this, we aim to introduce **artificial ("synthetic") variables** that influence car behavior and performance.

## Educational Focus

Students will be encouraged to:

- Contribute ideas to the **design of cars**
- Help design **race tracks**
- Propose and implement **obstacles**
- Experiment with AI behavior and tuning

## Core Gameplay Choice

The most important decision for each student will be their car’s **engine**, which represents the **pathfinding algorithm** controlling it.

## Upgrade & Economy System (Planned)

We plan to introduce:

- Swappable car parts
- A points-based or economy system
- Limited upgrade points to encourage strategic choices

## Supported / Planned Algorithms

Algorithms we aim to support include:

- Depth-First Search (DFS)
- Breadth-First Search (BFS)
- Dijkstra’s Algorithm
- A* Search
- Jump Point Search (JPS)

## Custom Car Design

Users can design their own cars using Pixilart:  
https://www.pixilart.com/draw

A template is available in the assets dir assets/car_template.png for download.

---

## Running the Game in the Browser

1. Install pygbag:
   ```bash
   python -m pip install pygbag
   ```
2. Run pygbag:
    ```bash
    python -m pygbag .
    ```
3. Open browser & navigate to: http://localhost:8000

## Running the Game via Terminal:

1. Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
2. Run the main.py file:
    ```bash
    python main.py
    ```

---

