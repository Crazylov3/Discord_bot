import pygame
import os
os.environ['SDL_VIDEODRIVER'] = 'dummy'
def create_user_board(guild_id,name_user,*args):
    pygame.font.init()
    pygame.init()
    images = {}
    for i in args:
        images[i] = None
    for key in images.keys():
        images[key] = pygame.image.load(f"cogs/GameAPI/Images/{key}.png")
    SCREEN = pygame.display.set_mode((700, 270))
    SCREEN.fill((0, 181, 63))
    for i,key in enumerate(args):
        SCREEN.blit(images[key], (35+i*35, 10))
    if not os.path.exists(f"cogs/GameAPI/playing_guild/{guild_id}"):
        os.makedirs(f"cogs/GameAPI/playing_guild/{guild_id}")
    pygame.image.save(SCREEN, f"cogs/GameAPI/playing_guild/{guild_id}/{name_user}.png")
    pygame.quit()

def create_current_board(guild_id,*args):
    pygame.font.init()
    pygame.init()
    images = {}
    for i in args:
        images[i] = None
    for key in images.keys():
        images[key] = pygame.image.load(f"cogs/GameAPI/Images/{key}.png")
    SCREEN = pygame.display.set_mode((700, 350))
    SCREEN.fill((0, 181, 63))
    x = (535-len(args)*35)//2
    for i,key in enumerate(args):
        SCREEN.blit(images[key], (x+i*35, 50))
    if not os.path.exists(f"cogs/GameAPI/playing_guild/{guild_id}"):
        os.makedirs(f"cogs/GameAPI/playing_guild/{guild_id}")
    pygame.image.save(SCREEN, f"cogs/GameAPI/playing_guild/{guild_id}/0current.png")
    pygame.quit()

