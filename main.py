# main.py
import asyncio
import pygame


WIN = pygame.display.set_mode((500,500))
pygame.display.set_caption("DFA PathFinding GrandPrix")

async def main():
    clock = pygame.time.Clock()

    
    while True:
        

        # -------------------------------
        # Draw Menu (before racing)
        # -------------------------------
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        WIN.fill((255, 0, 0))
        pygame.display.flip()
        await asyncio.sleep(0)
        dt = clock.tick(60) / 1000.0
    return 0

#if __name__ == "__main__":
asyncio.run(main())
