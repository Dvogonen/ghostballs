from random import randrange
import ftplib
import pygame

pygame.init()

# static global variables
directions = {"left": (-1, 0), "right": (1, 0), "up": (0, -1), "down": (0, 1), "stopped": (0, 0)}
small_font = pygame.font.Font('freesansbold.ttf', 18)
big_font = pygame.font.Font('freesansbold.ttf', 36)


class Tracks:
    def __init__(self, file_name: str):
        self.file_name = file_name
        file_handle = open(self.file_name, 'r')
        data = file_handle.read()
        file_handle.close()
        data_string = data.translate("utf-8")
        self.data = self.parse_structure(data_string, ['-', ':', ','])

    def parse_structure(self, data_string: str, parse_tokens: list):
        if len(parse_tokens) == 0:
            return []
        elif len(parse_tokens) == 1:
            leaves = data_string.split(parse_tokens[0])
            return int(leaves[0]), int(leaves[1])
        else:
            a = []
            token = parse_tokens[0]
            data_strings = data_string.split(token)
            for string in data_strings:
                a.append(self.parse_structure(string, parse_tokens[1:]))
            return a

    def build_string(self):
        result = ''
        for track in self.data:
            for tu in track:
                result = result + str(tu[0]) + ',' + str(tu[1]) + ':'
            result = result.rstrip(':')
            result = result + '-'
        result = result.rstrip('-')
        while '--' in result:
            result = result.replace('--', '-')
        return result

    def save(self):
        data = self.build_string()
        file_handle = open(self.file_name, 'w')
        file_handle.write(data)
        file_handle.close()

    def move_left(self, index):
        if index < 1:
            return False
        if index > (len(self.data) - 1):
            return False
        track = self.data[index]
        self.data.remove(track)
        self.data.insert(index - 1, track)
        return True

    def move_up(self, index):
        if index >= (len(self.data) - 1):
            return False
        track = self.data[index]
        self.data.remove(track)
        self.data.insert(index + 1, track)
        return True


class Color:
    background = (0, 0, 0)
    cursor = (255, 100, 0)
    defender_border = (100, 100, 100)
    text = (200, 200, 200)
    target = (175, 175, 0)
    block = (225, 225, 225)
    grey = (100, 100, 100)


color = Color()


# dynamic global variables collected in class
class Globals:
    def __init__(self):
        self.next_track = False
        self.previous_track = False
        self.exit = False
        self.track_index = 0
        self.sqr_size = 10


class Board:
    def __init__(self):
        self.size = (40, 60)


class Info:
    def __init__(self, top_position):
        global g
        self.positions = (40, 12)
        self.top_pos = top_position
        self.info_rect = (
            top_position[0], top_position[1], self.positions[0] * g.sqr_size, self.positions[1] * g.sqr_size)

    def draw_text(self, text: str, pos, font=small_font):
        global g
        text_object = font.render(text, True, color.text)
        text_rect = text_object.get_rect()
        text_rect = (
            self.top_pos[0] + pos[0] * g.sqr_size, self.top_pos[1] + pos[1] * g.sqr_size, text_rect[2], text_rect[3])
        window.blit(text_object, text_rect)

    def draw(self):
        global g
        pygame.draw.rect(window, color.background, self.info_rect)
        pygame.draw.rect(window, color.grey,
                         (self.top_pos[0], self.top_pos[1], self.positions[0] * g.sqr_size, g.sqr_size))
        self.draw_text("Track: " + str(g.track_index), (0, 2), big_font)
        self.draw_text("F1: Shift Track Up", (0, 8))
        self.draw_text("F2: Shift Track Down", (0, 10))
        self.draw_text("PgUp: Next Track", (22, 2))
        self.draw_text("PgDwn: Prev. Track", (22, 4))
        self.draw_text("Insert: Add Track", (22, 8))
        self.draw_text("Delete: Delete Track", (22, 10))


class Frame:
    def __init__(self):
        global g
        self.board = Board()
        self.info = Info((0, self.board.size[1] * g.sqr_size))

    @staticmethod
    def reset():
        window.fill(0)

    def hit(self, pos):
        if pos[0] < 0 or pos[1] < 0:
            return True
        if pos[0] >= self.board.size[0] or pos[1] > self.board.size[1] - 1:
            return True
        return False

    def positions(self):
        if self.board.size[0] >= self.info.positions[0]:
            x = self.board.size[0]
        else:
            x = self.info.positions[0]
        y = self.board.size[1] + self.info.positions[1]
        return x, y

    def x_size(self):
        global g
        return self.positions()[0] * g.sqr_size

    def y_size(self):
        global g
        return self.positions()[1] * g.sqr_size

    def draw(self):
        self.info.draw()


class Targets:
    def __init__(self, frame_param, tracks):
        self.frame = frame_param
        self.tracks = tracks
        self.positions = []
        self.reset()

    def reset(self):
        global g
        self.positions = self.tracks[g.track_index]

    def switch(self, pos):
        if pos not in self.positions:
            self.positions.append(pos)
        else:
            self.positions.remove(pos)

    @staticmethod
    def draw_cell(pos, color_param):
        global g
        pygame.draw.circle(window, color_param, (pos[0] * g.sqr_size + g.sqr_size // 2,
                                                 pos[1] * g.sqr_size + g.sqr_size // 2),
                           g.sqr_size // 2)

    def draw(self):
        for pos in self.positions:
            self.draw_cell(pos, color.target)


class Blocks:
    def __init__(self, frame_param, tracks):
        self.frame = frame_param
        self.tracks = tracks
        self.positions = []
        self.reset()

    def reset(self):
        global g
        self.positions = self.tracks[g.track_index]

    def switch(self, pos):
        if pos not in self.positions:
            self.positions.append(pos)
        else:
            self.positions.remove(pos)

    @staticmethod
    def draw_cell(pos, color_param):
        global g
        pygame.draw.circle(window, color_param, (pos[0] * g.sqr_size + g.sqr_size // 2,
                                                 pos[1] * g.sqr_size + g.sqr_size // 2),
                           g.sqr_size // 2)

    def draw(self):
        for pos in self.positions:
            self.draw_cell(pos, color.block)


class Cursor:
    def __init__(self, frame_param):
        self.frame = frame_param
        self.start_pos = (frame_param.board.size[0] // 2, frame_param.board.size[1] - 1)
        self.pos = self.start_pos
        self.old_pos = self.start_pos
        self.toward = directions['stopped']

    def reset(self):
        self.pos = self.start_pos
        self.old_pos = self.start_pos
        self.toward = directions['stopped']

    @staticmethod
    def draw_cell(pos, color_param):
        global g
        pygame.draw.rect(window, color_param, (pos[0] * g.sqr_size, pos[1] * g.sqr_size, g.sqr_size, g.sqr_size))

    def draw(self):
        self.draw_cell(self.old_pos, color.background)
        self.draw_cell(self.pos, color.cursor)

    def step(self):
        if self.toward != directions['stopped']:
            new_pos = (self.pos[0] + self.toward[0], self.pos[1] + self.toward[1])
            if not self.frame.hit(new_pos):
                self.old_pos = self.pos
                self.pos = new_pos


# global objects
target_positions = Tracks('gbtargets.txt')
block_positions = Tracks('gbblocks.txt')
g = Globals()
frame = Frame()
targets = Targets(frame, target_positions.data)
blocks = Blocks(frame, block_positions.data)
cursor = Cursor(frame)
window = pygame.display.set_mode((frame.x_size(), frame.y_size()))
pygame.display.set_caption("Ghost Balls Editor")
display_counter = 0
stop_counter = 0

while not g.exit:
    pygame.time.delay(10)
    if stop_counter > 0:
        stop_counter -= 1
    else:
        display_counter += 1

    if g.next_track:
        g.track_index += 1
        if g.track_index >= len(target_positions.data):
            g.track_index = 0

    if g.previous_track:
        g.track_index -= 1
        if g.track_index < 0:
            g.track_index = len(target_positions.data) - 1

    if g.next_track or g.previous_track:
        g.next_track = False
        g.previous_track = False
        frame.reset()
        targets.reset()
        blocks.reset()

    frame.draw()
    cursor.draw()
    targets.draw()
    blocks.draw()
    pygame.display.update()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            g.exit = True
        if event.type == pygame.KEYDOWN:
            display_counter = 0
            stop_counter = 8
            if event.key == pygame.K_LEFT:
                cursor.toward = directions['left']
            elif event.key == pygame.K_RIGHT:
                cursor.toward = directions['right']
            elif event.key == pygame.K_UP:
                cursor.toward = directions['up']
            elif event.key == pygame.K_DOWN:
                cursor.toward = directions['down']
            elif event.key == pygame.K_t:
                targets.switch(cursor.pos)
            elif event.key == pygame.K_b:
                blocks.switch(cursor.pos)
            elif event.key == pygame.K_PAGEUP:
                g.next_track = True
            elif event.key == pygame.K_PAGEDOWN:
                g.previous_track = True
            elif event.key == pygame.K_F1:
                target_positions.move_up(g.track_index)
                if block_positions.move_up(g.track_index):
                    g.next_track = True
            elif event.key == pygame.K_F2:
                target_positions.move_left(g.track_index)
                if block_positions.move_left(g.track_index):
                    g.previous_track = True
            elif event.key == pygame.K_ESCAPE:
                g.exit = True
            elif event.key == pygame.K_INSERT:
                target_positions.data.insert(g.track_index + 1, [])
                block_positions.data.insert(g.track_index + 1, [])
                g.next_track = True
            elif event.key == pygame.K_DELETE:
                if len(target_positions.data) > 0:
                    target_positions.data.remove(target_positions.data[g.track_index])
                    block_positions.data.remove(block_positions.data[g.track_index])
                    g.previous_track = True
        if event.type == pygame.KEYUP:
            cursor.toward = directions['stopped']

    # Manage movements
    if stop_counter == 0 and display_counter % 10 == 0:
        cursor.step()

# We have fallen off the main loop, so this is the end
target_positions.save()
block_positions.save()
pygame.quit()
