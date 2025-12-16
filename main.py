import pygame
import time
import random
import math
from utils import scale_image, bilt_rotate_center

# loading images that are scaled to size
GRASS = scale_image(pygame.image.load('assets/grass.jpg'), 2.5)
TRACK = scale_image(pygame.image.load('assets/track.png'), 1)
TRACK_BORDER = scale_image(pygame.image.load('assets/track-border.png'), 1)
TRACK_BORDER_MASK = pygame.mask.from_surface(TRACK_BORDER) # mask created using track border
FINISH = pygame.image.load('assets/finish.png')
FINISH_MASK = pygame.mask.from_surface(FINISH) # create a mask based off finish
RED_CAR = scale_image(pygame.image.load('assets/red-car.png'), 0.55)
GREEN_CAR = scale_image(pygame.image.load('assets/green-car.png'), 0.55)

WIN = pygame.display.set_mode((TRACK.get_width(), TRACK.get_height()))
pygame.display.set_caption("DFA Path Finding Grand Prix")

FPS = 60

class Car:
    def __init__(self, max_vel, rotation_vel):
        self.img = self.IMG
        self.max_vel = max_vel
        self.vel = 0
        self.rotation_vel = rotation_vel
        self.angle = 0
        self.x, self.y = self.START_POS
        self.acceleration = 0.5
    
    def rotate(self, left=False, right=False):
        if left:
            self.angle += self.rotation_vel
        elif right:
            self.angle -= self.rotation_vel
    
    def draw(self, win):
        bilt_rotate_center(win, self.img, (self.x, self.y), self.angle)

    def move_forward(self):
        self.vel = min(self.vel + self.acceleration, self.max_vel)
        self.move()
    
    def move_backward(self):
        self.vel = max(self.vel - self.acceleration, -self.max_vel/2)
        self.move()
    
    def move(self):
        radians = math.radians(self.angle)
        vertical = math.cos(radians) * self.vel
        horizontal = math.sin(radians) * self.vel
        
        self.y -= vertical
        self.x -= horizontal
    
    def reduce_speed(self):
        self.vel = max(self.vel - self.acceleration/2, 0)
        self.move()
    
    def collide(self, mask, x=0, y=0):
        car_mask = pygame.mask.from_surface(self.img)
        offset = (int(self.x - x), int(self.y - y))
        poi = mask.overlap(car_mask, offset)
        return poi
    
    def reset(self):
        self.x, self.y = self.START_POS
        self.angle = 0
        self.vel = 0




class PlayerCar(Car):
    IMG = RED_CAR
    START_POS = (180, 200)

    def bounce(self):
        self.vel = -self.vel
        self.move()



def draw(win, images, player_car):
    for img, pos in images:
        win.blit(img, pos)
    player_car.draw(win)
    pygame.display.update()

def move_player(player_car):
    keys = pygame.key.get_pressed()
    moved = False
    if keys [pygame.K_a]:
        player_car.rotate(left=True)
    if keys [pygame.K_d]:
        player_car.rotate(right=True)
    if keys [pygame.K_w]:
        moved = True
        player_car.move_forward()
    if keys [pygame.K_s]:
        moved = True
        player_car.move_backward()
    if not moved:
        player_car.reduce_speed()

run = True
clock = pygame.time.Clock()

images = [ # dict of images and their positions
    (GRASS, (0, 0)),
    (TRACK, (0, 0)),
    (FINISH, (140, 250)),
    (TRACK_BORDER, (0, 0)),]

player_car = PlayerCar(5,5)

while run:
    clock.tick(FPS)

    draw(WIN, images, player_car)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            run = False
            break
    
    move_player(player_car)

    if player_car.collide(TRACK_BORDER_MASK) != None:
        # print("collide") # test collision occuring
        player_car.bounce()
    
    finish_poi_collide = player_car.collide(FINISH_MASK, 140, 250)
    if finish_poi_collide != None:
        # print(finish_poi_collide) test collision occuring
        if finish_poi_collide[1] == 0:
            player_car.bounce()
        else:
            player_car.reset()
            print("FINISH!")


pygame.quit()