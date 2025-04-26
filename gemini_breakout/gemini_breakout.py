import pygame
import sys
import math
import os
import google.generativeai as genai
from dotenv import load_dotenv

# --- Constants ---
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
PADDLE_WIDTH = 100
PADDLE_HEIGHT = 15
BALL_SIZE = 10
BRICK_WIDTH = 60
BRICK_HEIGHT = 20
BRICK_ROWS = 5
BRICK_COLS = 10
BRICK_GAP = 5
BALL_SPEED_START = 5
BALL_SPEED_INCREASE_PER_HIT = 0.1
PADDLE_SPEED = 7
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
GREEN = (0, 255, 0)
YELLOW = (255, 255, 0)
GRAY = (200, 200, 200)
FPS = 60

# --- Game States ---
STATE_MENU = 0
STATE_PLAYING = 1
STATE_GAME_OVER = 2
STATE_WIN = 3
STATE_PAUSED = 4
STATE_GEMINI_TIP = 5

# --- Gemini Integration ---
GEMINI_MODEL_NAME = 'gemini-2.5-flash-preview-04-17' # Using Flash for lower latency/cost
GEMINI_PROMPT = "Give me a helpful tip or interesting fact about the classic arcade game Breakout."
GEMINI_GENERATING_MESSAGE = "Consulting Gemini..."
GEMINI_ERROR_MESSAGE = "Error getting tip from Gemini."
GEMINI_NO_KEY_MESSAGE = "GOOGLE_API_KEY not set!"

# --- Pygame Setup ---
pygame.init()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Breakout with Gemini")
clock = pygame.time.Clock()
font = pygame.font.Font(None, 36) # Default font, size 36

# --- Gemini Setup ---
gemini_model = None
try:
    load_dotenv()
    genai.configure(api_key=os.environ['GEMINI_API_KEY'])
    gemini_model = genai.GenerativeModel(GEMINI_MODEL_NAME)
    print("Gemini model configured successfully.")
except Exception as e:
    print(f"Error configuring Gemini model: {e}")
    gemini_model = False # Mark as failed to configure

# --- Classes ---

class Paddle(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.image = pygame.Surface([PADDLE_WIDTH, PADDLE_HEIGHT])
        self.image.fill(WHITE)
        self.rect = self.image.get_rect()
        self.rect.x = (SCREEN_WIDTH - PADDLE_WIDTH) // 2
        self.rect.y = SCREEN_HEIGHT - PADDLE_HEIGHT - 10
        self.speed = 0

    def update(self):
        self.rect.x += self.speed
        # Keep paddle within screen bounds
        if self.rect.left < 0:
            self.rect.left = 0
        if self.rect.right > SCREEN_WIDTH:
            self.rect.right = SCREEN_WIDTH

class Ball(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.image = pygame.Surface([BALL_SIZE, BALL_SIZE])
        self.image.fill(WHITE)
        self.rect = self.image.get_rect()
        self.rect.x = SCREEN_WIDTH // 2
        self.rect.y = SCREEN_HEIGHT // 2
        self.dx = BALL_SPEED_START # Initial horizontal speed
        self.dy = BALL_SPEED_START # Initial vertical speed
        self.speed = BALL_SPEED_START

    def update(self):
        self.rect.x += self.dx
        self.rect.y += self.dy

    def reset(self):
        self.rect.x = SCREEN_WIDTH // 2
        self.rect.y = SCREEN_HEIGHT // 2
        self.speed = BALL_SPEED_START
        # Reset direction, maybe random horizontal
        self.dx = BALL_SPEED_START * (1 if pygame.time.get_ticks() % 2 == 0 else -1)
        self.dy = BALL_SPEED_START # Always start moving up


class Brick(pygame.sprite.Sprite):
    def __init__(self, x, y, color):
        super().__init__()
        self.image = pygame.Surface([BRICK_WIDTH, BRICK_HEIGHT])
        self.image.fill(color)
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y

# --- Game Functions ---

def create_bricks():
    bricks = pygame.sprite.Group()
    colors = [RED, YELLOW, GREEN, BLUE, WHITE] # Example colors for rows
    start_x = (SCREEN_WIDTH - (BRICK_COLS * (BRICK_WIDTH + BRICK_GAP) - BRICK_GAP)) // 2
    start_y = 50 # Start bricks from top
    for row in range(BRICK_ROWS):
        for col in range(BRICK_COLS):
            x = start_x + col * (BRICK_WIDTH + BRICK_GAP)
            y = start_y + row * (BRICK_HEIGHT + BRICK_GAP)
            color = colors[row % len(colors)] # Cycle through colors
            brick = Brick(x, y, color)
            bricks.add(brick)
    return bricks

def draw_text(surface, text, color, x, y, center=False):
    text_surface = font.render(text, True, color)
    text_rect = text_surface.get_rect()
    if center:
        text_rect.center = (x, y)
    else:
         text_rect.topleft = (x, y)
    surface.blit(text_surface, text_rect)

def wrap_text(surface, text, color, x, y, max_width, line_spacing=5):
    words = text.split(' ')
    lines = []
    current_line = ""
    for word in words:
        # Check if adding the next word exceeds max width
        test_line = current_line + word + " " if current_line else word
        test_surface = font.render(test_line, True, color)
        if test_surface.get_width() > max_width:
            # Start a new line
            lines.append(current_line)
            current_line = word + " "
        else:
            current_line = test_line
    lines.append(current_line) # Add the last line

    current_y = y
    for line in lines:
        draw_text(surface, line.strip(), color, x, current_y)
        current_y += font.get_linesize() + line_spacing


# --- Main Game Loop ---

def main():
    global game_state # Need to modify global game state

    # --- Game Variables ---
    score = 0
    lives = 3
    game_state = STATE_MENU
    gemini_tip_text = None
    gemini_generating = False

    # --- Sprite Groups ---
    all_sprites = pygame.sprite.Group()
    bricks = pygame.sprite.Group()
    paddle = Paddle()
    ball = Ball()

    # --- Initial Setup ---
    all_sprites.add(paddle, ball)
    bricks = create_bricks() # Create initial set of bricks

    # --- Menu Loop ---
    while game_state == STATE_MENU:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                game_state = STATE_PLAYING # Start game on any key press

        screen.fill(BLACK)
        draw_text(screen, "Breakout!", WHITE, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 3, center=True)
        draw_text(screen, "Press any key to start", WHITE, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2, center=True)
        draw_text(screen, "Press 'G' for a Gemini tip (during gameplay or pause)", GRAY, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 1.5, center=True)
        pygame.display.flip()
        clock.tick(FPS)

    # --- Game Loop ---
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_LEFT:
                    paddle.speed = -PADDLE_SPEED
                elif event.key == pygame.K_RIGHT:
                    paddle.speed = PADDLE_SPEED
                elif event.key == pygame.K_p:
                    # Toggle pause only if playing
                    if game_state == STATE_PLAYING:
                        game_state = STATE_PAUSED
                    elif game_state == STATE_PAUSED:
                        game_state = STATE_PLAYING
                elif event.key == pygame.K_g:
                    # Trigger Gemini tip if not already generating and key is available
                    if game_state != STATE_GEMINI_TIP and not gemini_generating and gemini_model:
                        game_state = STATE_GEMINI_TIP
                        gemini_generating = True
                        gemini_tip_text = None # Clear previous tip
                        # Note: This will block the main loop while generating.
                        # For a real-time game, this should be done in a thread.
                        # But for a paused/state change, it's acceptable here.
                        try:
                            print("Sending prompt to Gemini...")
                            response = gemini_model.generate_content(GEMINI_PROMPT)
                            print("Received response.")
                            gemini_tip_text = response.text
                        except Exception as e:
                            print(f"Gemini API error: {e}")
                            gemini_tip_text = GEMINI_ERROR_MESSAGE
                        finally:
                            gemini_generating = False # Done generating
                    elif not gemini_model and game_state != STATE_GEMINI_TIP:
                         gemini_tip_text = GEMINI_NO_KEY_MESSAGE
                         game_state = STATE_GEMINI_TIP # Show key error message
                    elif game_state == STATE_GEMINI_TIP:
                         # Exit Gemini tip mode on 'G' or 'Escape'
                         game_state = STATE_PAUSED # Return to pause state after tip
                         gemini_tip_text = None # Hide tip
                elif event.key == pygame.K_ESCAPE:
                     if game_state == STATE_GEMINI_TIP:
                         game_state = STATE_PAUSED # Exit Gemini tip mode
                         gemini_tip_text = None # Hide tip
                     elif game_state == STATE_PAUSED:
                          game_state = STATE_PLAYING # Exit pause
                     elif game_state in (STATE_GAME_OVER, STATE_WIN):
                         main() # Restart game (simple way)


            elif event.type == pygame.KEYUP:
                if event.key == pygame.K_LEFT and paddle.speed < 0:
                    paddle.speed = 0
                elif event.key == pygame.K_RIGHT and paddle.speed > 0:
                    paddle.speed = 0

        # --- Game Logic ---
        if game_state == STATE_PLAYING:
            all_sprites.update() # Update paddle and ball

            # Ball collision with walls
            if ball.rect.left < 0 or ball.rect.right > SCREEN_WIDTH:
                ball.dx *= -1 # Bounce off left/right walls
            if ball.rect.top < 0:
                ball.dy *= -1 # Bounce off top wall
            # Collision with bottom wall (lose a life)
            if ball.rect.bottom > SCREEN_HEIGHT:
                lives -= 1
                if lives <= 0:
                    game_state = STATE_GAME_OVER
                else:
                    ball.reset() # Reset ball position and speed
                    paddle.rect.x = (SCREEN_WIDTH - PADDLE_WIDTH) // 2 # Reset paddle position

            # Ball collision with paddle
            if pygame.sprite.collide_rect(ball, paddle):
                # Prevent sticky ball by ensuring it's moving down
                if ball.dy > 0:
                    ball.dy *= -1 # Bounce up
                    # Add a bit of horizontal speed based on where it hit the paddle
                    hit_pos = ball.rect.centerx - paddle.rect.centerx
                    ball.dx = (hit_pos / (PADDLE_WIDTH / 2)) * ball.speed # Max speed change at edges
                    ball.speed += BALL_SPEED_INCREASE_PER_HIT # Slightly increase speed

                    # Normalize dx, dy to maintain consistent total speed
                    speed_magnitude = math.sqrt(ball.dx**2 + ball.dy**2)
                    if speed_magnitude > 0: # Avoid division by zero
                         ball.dx = (ball.dx / speed_magnitude) * ball.speed
                         ball.dy = (ball.dy / speed_magnitude) * ball.speed

            # Ball collision with bricks
            # Use pygame.sprite.spritecollide for efficient collision detection
            hit_bricks = pygame.sprite.spritecollide(ball, bricks, True) # True removes the brick
            for brick in hit_bricks:
                score += 10 # Increase score for each hit brick
                ball.dy *= -1 # Bounce off brick
                ball.speed += BALL_SPEED_INCREASE_PER_HIT # Slightly increase speed

                # Normalize dx, dy based on new speed
                speed_magnitude = math.sqrt(ball.dx**2 + ball.dy**2)
                if speed_magnitude > 0:
                     ball.dx = (ball.dx / speed_magnitude) * ball.speed
                     ball.dy = (ball.dy / speed_magnitude) * ball.speed


            # Check for win condition
            if len(bricks) == 0:
                game_state = STATE_WIN

        # --- Drawing ---
        screen.fill(BLACK)

        # Draw sprites
        all_sprites.draw(screen)
        bricks.draw(screen)

        # Draw score and lives
        draw_text(screen, f"Score: {score}", WHITE, 10, 10)
        draw_text(screen, f"Lives: {lives}", WHITE, SCREEN_WIDTH - 100, 10)

        # Draw state messages
        if game_state == STATE_PAUSED:
            draw_text(screen, "PAUSED", WHITE, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2, center=True)
            draw_text(screen, "(Press P to resume)", WHITE, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 40, center=True)
            draw_text(screen, "(Press G for Gemini tip)", WHITE, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 80, center=True)
        elif game_state == STATE_GAME_OVER:
            draw_text(screen, "GAME OVER", RED, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2, center=True)
            draw_text(screen, f"Final Score: {score}", WHITE, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 40, center=True)
            draw_text(screen, "(Press ESC to restart)", WHITE, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 80, center=True)
        elif game_state == STATE_WIN:
            draw_text(screen, "YOU WIN!", GREEN, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2, center=True)
            draw_text(screen, f"Final Score: {score}", WHITE, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 40, center=True)
            draw_text(screen, "(Press ESC to restart)", WHITE, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 80, center=True)
        elif game_state == STATE_GEMINI_TIP:
            # Darken screen slightly
            s = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            s.fill((0, 0, 0, 180)) # Transparent black
            screen.blit(s, (0, 0))

            # Draw Gemini prompt box
            box_width = SCREEN_WIDTH * 0.8
            box_height = SCREEN_HEIGHT * 0.6
            box_x = (SCREEN_WIDTH - box_width) // 2
            box_y = (SCREEN_HEIGHT - box_height) // 2
            pygame.draw.rect(screen, BLUE, (box_x, box_y, box_width, box_height), 0) # Filled rectangle
            pygame.draw.rect(screen, WHITE, (box_x, box_y, box_width, box_height), 2) # Border

            # Draw title and content
            draw_text(screen, "Gemini Tip", WHITE, box_x + 20, box_y + 20)
            pygame.draw.line(screen, WHITE, (box_x + 20, box_y + 55), (box_x + box_width - 20, box_y + 55), 1) # Separator line

            content_x = box_x + 20
            content_y = box_y + 70
            content_width = box_width - 40

            if gemini_generating:
                 draw_text(screen, GEMINI_GENERATING_MESSAGE, YELLOW, content_x, content_y)
            elif gemini_tip_text:
                 wrap_text(screen, gemini_tip_text, WHITE, content_x, content_y, content_width)
            elif not gemini_model:
                 wrap_text(screen, GEMINI_NO_KEY_MESSAGE, RED, content_x, content_y, content_width)


            draw_text(screen, "(Press G or ESC to close)", GRAY, SCREEN_WIDTH // 2, box_y + box_height - 40, center=True)


        # --- Update Display ---
        pygame.display.flip()

        # --- Cap the frame rate ---
        clock.tick(FPS)

    pygame.quit()
    sys.exit()

# --- Start the game ---
if __name__ == "__main__":
    game_state = STATE_MENU # Initial state before calling main
    main()
