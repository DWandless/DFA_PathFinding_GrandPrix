import pygame

def scale_image(image, factor): # Scales a Pygame image by a given factor
    size = round(image.get_width() * factor), round(image.get_height() * factor)
    return pygame.transform.scale(image, size)

def bilt_rotate_center(win, image, top_left, angle):
    rotated_image = pygame.transform.rotate(image, angle)
    new_rect = rotated_image.get_rect(center=image.get_rect(topleft = top_left).center)
    win.blit(rotated_image, new_rect.topleft)