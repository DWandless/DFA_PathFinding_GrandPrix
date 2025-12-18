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

PATH = [(191, 131), (138, 80), (70, 135), (70, 514), (317, 785), (397, 811), (450, 753), (457, 586), (559, 532), (663, 596), (669, 753), (741, 814), (824, 746), (821, 469), (757, 400), (502, 398), (446, 347), (514, 288), (763, 282), (822, 238), (820, 130), (749, 83), (363, 86), (316, 150), (310, 405), (255, 460), (198, 404), (193, 263)]
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
    START_POS = (185, 200)

    def bounce(self):
        self.vel = -self.vel
        self.move()

class ComputerCar(Car):
    IMG = GREEN_CAR
    START_POS = (165, 200)

    def __init__(self, max_vel, rotation_vel, path=[]):
        super().__init__(max_vel, rotation_vel)
        self.path = path
        self.current_point = 0
        self.vel = max_vel
    
    def draw_points(self, win):
        for point in self.path:
            pygame.draw.circle(win, (255, 0, 0), point, 5)

    def draw(self, win):
        super().draw(win)
        # self.draw_points(win)
    
    def calculate_angle(self):
        target_x, target_y = self.path[self.current_point]
        x_diff = target_x - self.x
        y_diff = target_y - self.y

        if y_diff == 0:
            desired_radian_angle = math.pi / 2
        else:
            desired_radian_angle = math.atan(x_diff / y_diff)
        if target_y > self.y:
            desired_radian_angle += math.pi
        
        difference_in_angle = self.angle - math.degrees(desired_radian_angle)
        if difference_in_angle >= 180:
            difference_in_angle -= 360

        if difference_in_angle > 0:
            self.angle -= min(self.rotation_vel, abs(difference_in_angle))
        else:
            self.angle += min(self.rotation_vel, abs(difference_in_angle))
    
    def update_path_point(self):
        target = self.path[self.current_point]
        rect = pygame.Rect(self.x, self.y, self.img.get_width(), self.img.get_height())
        if rect.collidepoint(*target):
            self.current_point += 1

    def move(self):
        if self.current_point >= len(self.path):
            return
        
        self.calculate_angle()
        self.update_path_point()
        super().move()
        
        target_x, target_y = self.path[self.current_point]
        car_vector = pygame.math.Vector2(self.x, self.y)
        target_vector = pygame.math.Vector2(target_x, target_y)
        distance = target_vector - car_vector

        if distance.length() < self.vel:
            self.current_point += 1
        else:
            distance = distance.normalize()
            distance = distance * self.vel
            self.x += distance.x
            self.y += distance.y
 
def draw(win, images, player_car, computer_car):
    for img, pos in images:
        win.blit(img, pos)
    player_car.draw(win)
    computer_car.draw(win)
    pygame.display.update()

# control tied to button inputs
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

def handle_collision(player_car, computer_car):
    
    if player_car.collide(TRACK_BORDER_MASK) != None:
        # print("collide") # test collision occuring
        player_car.bounce()

    computer_finish_poi_collide = computer_car.collide(FINISH_MASK, 140, 250)
    if computer_finish_poi_collide != None:
        player_car.reset()
        computer_car.reset()
        print("COMPUTER WINS!")

    player_finish_poi_collide = player_car.collide(FINISH_MASK, 140, 250)
    if player_finish_poi_collide != None:
        # print(finish_poi_collide) test collision occuring
        if player_finish_poi_collide[1] == 0:
            player_car.bounce()
        else:
            player_car.reset()
            computer_car.reset()
            print("PLAYER WINS!")

run = True
clock = pygame.time.Clock()

images = [ # dict of images and their positions
    (GRASS, (0, 0)),
    (TRACK, (0, 0)),
    (FINISH, (140, 250)),
    (TRACK_BORDER, (0, 0)),]

player_car = PlayerCar(4,4)
computer_car = ComputerCar(2, 4, PATH)

while run:
    clock.tick(FPS)

    draw(WIN, images, player_car, computer_car)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            run = False
            break
        
        """
        # used for finding a set path of track for computer car to use
        if event.type == pygame.MOUSEBUTTONDOWN:
            pos = pygame.mouse.get_pos()
            computer_car.path.append(pos)
        """
    
    move_player(player_car)
    computer_car.move()

    handle_collision(player_car, computer_car)

print(computer_car.path)
pygame.quit()