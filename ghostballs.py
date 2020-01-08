import ftplib

import pygame

pygame.init()

# static global variables
directions = {"left": (-1, 0), "right": (1, 0), "up": (0, -1), "down": (0, 1), "stopped": (0, 0)}
click_sound = pygame.mixer.Sound('click.wav')
count_sound = pygame.mixer.Sound('count_in.wav')
font = pygame.font.Font('freesansbold.ttf', 40)


class Tracks:
    def __init__(self, file_name: str):
        self.file_name = file_name
        self.data = []
        self.reset()

    def reset(self):
        tracks_file = open(self.file_name, 'r')
        data = tracks_file.read()
        tracks_file.close()
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


class Color:
    background = (0, 0, 100)
    ball = (255, 100, 0)
    ball_original = ball
    defender = (255, 100, 0)
    defender_border = (100, 100, 100)
    text = (200, 200, 200)
    target = (200, 200, 0)
    target_original = target
    block = (200, 200, 200)
    block_original = block
    grey = (175, 175, 175)

    def dimmer(self, color_param, steps) -> tuple:
        new_color = []
        cdiff = (
            color_param[0] - self.background[0], color_param[1] - self.background[1],
            color_param[2] - self.background[2])
        for i in range(len(color_param)):
            cstep = cdiff[i] // steps
            if cstep != 0:
                new_color.append(color_param[i] - cstep)
            else:
                new_color.append(self.background[i])
        return new_color[0], new_color[1], new_color[2]


color = Color()


# dynamic global variables collected in class
class Globals:
    def __init__(self):
        self.sqr_size = 10
        self.game_lost = False
        self.game_won = False
        self.display_counter = 0
        self.exit = False
        self.track_index = 0


class Board:
    def __init__(self):
        self.board_size = (40, 60)

    def draw(self):
        pygame.draw.rect(window, color.background, (
            0, 0, self.board_size[0] * g.sqr_size, self.board_size[1] * g.sqr_size))


class Info:
    def __init__(self, top_position: tuple):
        self.size = (40, 10)
        self.top_position = top_position
        self.hiscore = 0
        self.old_score = 0
        self.new_score = 0
        self.lives = 3
        self.max_lives = 10
        self.text_rec = (0, 0, 0, 0)

    def reset(self):
        self.lives = 3
        if self.new_score > self.hiscore:
            self.hiscore = self.new_score
        self.new_score = 0
        self.old_score = 0
        pygame.display.set_caption("Ghost Balls - Hiscore: " + str(self.hiscore))

    def draw(self):
        pygame.draw.rect(window, color.background, (
            self.top_position[0] * g.sqr_size, self.top_position[1] * g.sqr_size, self.size[0] * g.sqr_size,
            self.size[1] * g.sqr_size))
        pygame.draw.rect(window, color.grey, (
            self.top_position[0] * g.sqr_size, self.top_position[1] * g.sqr_size, self.size[0] * g.sqr_size,
            g.sqr_size))
        text = font.render("Score: " + str(self.new_score), True, color.text)
        self.text_rec = text.get_rect()
        self.text_rec.center = (200, 650)
        window.blit(text, self.text_rec)
        for i in range(self.max_lives):
            if i < self.lives - 1:
                col = color.ball
            else:
                col = color.background
            pygame.draw.circle(window, col, (i * 2 * g.sqr_size + g.sqr_size, 690), g.sqr_size // 2)


class Shaders:
    def __init__(self):
        self.items = []
        self.reset()

    def reset(self):
        self.items = []

    def add(self, positions, color_param):
        self.items.append([positions, color_param])

    def dim(self):
        for item in self.items:
            item[1] = color.dimmer(item[1], 16)
            if item[1] == (0, 0, 0):
                self.items.remove(item)

    def draw(self):
        for item in self.items:
            for pos in item[0]:
                pygame.draw.circle(window, item[1],
                                   (pos[0] * g.sqr_size + g.sqr_size // 2, pos[1] * g.sqr_size + g.sqr_size // 2),
                                   g.sqr_size // 2)


class Frame:
    def __init__(self, board_param: Board, info_param: Info):
        self.board = board_param
        self.info = info_param

    @staticmethod
    def reset():
        count_sound.play()
        pygame.time.delay(1000)
        pygame.display.update()
        pygame.time.delay(500)
        color.target = color.target_original
        color.block = color.block_original
        color.ball = color.ball_original

    def hit(self, pos: tuple) -> bool:
        if pos[0] < 0 or pos[1] < 0:
            click_sound.play()
            return True
        if pos[0] >= self.board.board_size[0] or pos[1] > self.board.board_size[1] - 1:
            click_sound.play()
            return True
        return False

    def size(self) -> tuple:
        if self.board.board_size[0] >= self.info.size[0]:
            x = self.board.board_size[0]
        else:
            x = self.info.size[0]
        y = self.board.board_size[1] + self.info.size[1]
        return x, y

    def x_size(self) -> int:
        return self.size()[0] * g.sqr_size

    def y_size(self):
        return self.size()[1] * g.sqr_size


class Targets:
    def __init__(self, frame_param: Frame, tracks: Tracks):
        self.frame = frame_param
        self.tracks = tracks
        self.positions = []
        self.reset()

    def reset(self):
        self.positions = self.tracks.data[g.track_index]

    @staticmethod
    def draw_cell(pos: tuple, color_param):
        pygame.draw.circle(window, color_param, (pos[0] * g.sqr_size + g.sqr_size // 2,
                                                 pos[1] * g.sqr_size + g.sqr_size // 2), g.sqr_size // 2)

    def draw(self):
        for pos in self.positions:
            self.draw_cell(pos, color.target)

    def find_new_friends(self, pos: tuple, friends: list):
        candidates = [(pos[0], pos[1] - 1), (pos[0] - 1, pos[1]), (pos[0] + 1, pos[1]), (pos[0], pos[1] + 1)]
        for candidate in candidates:
            if candidate in self.positions and candidate not in friends:
                friends.append(candidate)
                self.find_new_friends(candidate, friends)

    def hit(self, pos: tuple) -> bool:
        return_val = False
        if pos in self.positions:
            return_val = True
            friends = [pos]
            self.find_new_friends(pos, friends)
            for friend in friends:
                self.positions.remove(friend)
                self.draw_cell(friend, color.background)
            shaders.add(friends, color.target)
            click_sound.play()
            frame.info.old_score = frame.info.new_score
            frame.info.new_score += 1

        if not self.positions:
            g.game_won = True
        return return_val


class Blocks:
    def __init__(self, frame_param: Frame, tracks: Tracks):
        self.frame = frame_param
        self.tracks = tracks
        self.positions = []
        self.reset()

    def reset(self):
        self.positions = self.tracks.data[g.track_index]

    @staticmethod
    def draw_cell(pos: tuple, color_param):
        pygame.draw.circle(window, color_param,
                           (pos[0] * g.sqr_size + g.sqr_size // 2, pos[1] * g.sqr_size + g.sqr_size // 2),
                           g.sqr_size // 2)

    def draw(self):
        for pos in self.positions:
            self.draw_cell(pos, color.block)

    def hit(self, pos: tuple) -> bool:
        if pos in self.positions:
            click_sound.play()
            return True
        else:
            return False


class Defender:
    def __init__(self, frame_param: Frame):
        self.frame = frame_param
        self.start_pos = (frame_param.board.board_size[0] // 2, frame_param.board.board_size[1] - 1)
        self.pos = self.start_pos
        self.old_pos = self.start_pos
        self.toward = directions['stopped']

    def reset(self):
        self.pos = self.start_pos
        self.old_pos = self.start_pos
        self.toward = directions['stopped']

    def hit(self, pos: tuple) -> bool:
        poslist = []
        for x in range(-4, 5, 1):
            for y in range(-1, 1, 1):
                poslist.append((self.pos[0] + x, self.pos[1] + y))
        if pos in poslist:
            click_sound.play()
            color.target = color.target_original
            color.block = color.block_original
            color.ball = color.ball_original
            return True
        else:
            return False

    def bounce_direction(self, pos: tuple, direction) -> tuple:
        if pos[0] < self.pos[0] - 1:
            if direction[0] < 0:
                return -2, -direction[1]
            if direction[0] == 0:
                return -1, -direction[1]
            if direction[0] > 0:
                return 0, -direction[1]

        elif pos[0] > self.pos[0] + 1:
            if direction[0] < 0:
                return 0, -direction[1]
            if direction[0] == 0:
                return 1, -direction[1]
            if direction[0] > 0:
                return 2, -direction[1]

        else:
            if direction[0] < 0:
                return direction[0], -direction[1]
            if direction[0] == 0:
                return 0, -1
            if direction[0] > 0:
                return direction[0], -direction[1]

    @staticmethod
    def draw_cell(pos: tuple, color_param, bkr):
        pygame.draw.rect(window, bkr, (
            (pos[0] - 4) * g.sqr_size, (pos[1] - 1) * g.sqr_size, g.sqr_size * 9, g.sqr_size * 2))
        pygame.draw.rect(window, color_param, (
            (pos[0] - 4) * g.sqr_size + 1, (pos[1] - 1) * g.sqr_size + 1, g.sqr_size * 9 - 2, g.sqr_size * 2 - 2))

    def draw_shadow(self):
        self.draw_cell(self.old_pos, color.background, color.background)

    def draw(self):
        self.draw_cell(self.pos, color.defender, color.defender_border)

    def step(self):
        if self.toward != directions['stopped']:
            new_pos = (self.pos[0] + self.toward[0], self.pos[1] + self.toward[1])
            if not self.frame.hit(new_pos):
                self.old_pos = self.pos
                self.pos = new_pos


class Ball:
    def __init__(self, targets_param: Targets, blocks_param: Blocks, defender_param: Defender, frame_param: Frame):
        self.targets = targets_param
        self.blocks = blocks_param
        self.defender = defender_param
        self.frame = frame_param
        self.fired = False
        self.pos = (0, 0)
        self.old_pos = (0, 0)
        self.direction = (0, -1)
        self.reset()

    def reset(self):
        self.pos = (self.frame.board.board_size[0] // 2, self.frame.board.board_size[1] - 2)
        self.old_pos = self.pos
        self.fired = False
        self.direction = (0, -1)

    @staticmethod
    def draw_cell(pos: tuple, color_param):
        pygame.draw.circle(window, color_param,
                           (pos[0] * g.sqr_size + g.sqr_size // 2, pos[1] * g.sqr_size + g.sqr_size // 2),
                           g.sqr_size // 2)

    def draw_shadow(self):
        self.draw_cell(self.old_pos, color.background)

    def draw(self):
        self.draw_cell(self.pos, color.ball)

    def step(self):
        new_pos = (self.pos[0] + self.direction[0], self.pos[1] + self.direction[1])

        if self.defender.hit(new_pos):
            self.direction = self.defender.bounce_direction(new_pos, self.direction)

        elif new_pos[1] >= self.frame.board.board_size[1]:
            g.game_lost = True

        elif self.targets.hit(new_pos) or self.blocks.hit(new_pos):
            self.direction = (self.direction[0] * -1, self.direction[1] * -1)

        if self.frame.hit(new_pos):
            if (new_pos[0] < 0) or (new_pos[0] >= (self.frame.board.board_size[0])):
                self.direction = (self.direction[0] * -1, self.direction[1])
            if new_pos[1] < 0:
                self.direction = (self.direction[0], self.direction[1] * -1)

        self.old_pos = self.pos
        self.pos = new_pos

    def fire(self, pos: tuple):
        if not self.fired:
            self.fired = True
            self.pos = pos
            self.step()
            self.draw()


# global objects
target_positions = Tracks('gbtargets.txt')
block_positions = Tracks('gbblocks.txt')
g = Globals()
board = Board()
info = Info((0, board.board_size[1]))
frame = Frame(board, info)
targets = Targets(frame, target_positions)
blocks = Blocks(frame, block_positions)
shaders = Shaders()
defender = Defender(frame)
ball = Ball(targets, blocks, defender, frame)
window = pygame.display.set_mode((frame.x_size(), frame.y_size()))
pygame.display.set_caption("Ghost Balls")

# The hiscore storage and the storage function needs to be global
hiscore_raw_data = b""


def store_hiscore(data):
    global hiscore_raw_data
    hiscore_raw_data = data


def take_second(elem):
    return elem[1]


class Hiscore:
    def __init__(self, filename: str):
        self.hiscore_data_tulist = []
        self.filename = filename
        self.server = 'ftp.lillhagsvagen.se'
        self.username = 'xxxxxxxxxxx'
        self.password = 'xxxxxxxxxxx'
        self.text_rec = (0, 0, 0, 0)
        self.reset()

    def reset(self):
        data = self.read_remote_file()
        if data == '':
            data = self.read_local_file()
        self.hiscore_data_tulist = self.process_data(data)

    @staticmethod
    def process_data(data: str) -> list:
        data_list = data.split('\r\n')
        while '' in data_list:
            data_list.remove('')
        tulist = []
        for item in data_list:
            row = item.split()
            tulist.append((row[0], int(row[1])))
        tulist.sort(key=take_second, reverse=True)
        return tulist

    def read_remote_file(self) -> str:
        global hiscore_raw_data
        result = ""
        try:
            ftp = ftplib.FTP(self.server)
            ftp.login(self.username, self.password)
            ftp.retrbinary('RETR ' + self.filename, store_hiscore)
            ftp.quit()
            result = hiscore_raw_data.decode("utf-8")
        except ftplib.all_errors:
            pass
        return result

    def read_local_file(self) -> str:
        result = ''
        try:
            hiscore_file = open(self.filename, 'rb')
            raw_data = hiscore_file.read()
            result = raw_data.decode("utf-8")
        except:
            pass
        return result

    def save_local_file(self) -> bool:
        try:
            hiscore_file = open(self.filename, 'w')
            for tu in self.hiscore_data_tulist:
                hiscore_file.write(tu[0] + " " + str(tu[1]) + "\n")
            hiscore_file.close()
            return True
        except:
            return False

    def save_remote_file(self) -> bool:
        self.save_local_file()
        try:
            hiscore_file = open(self.filename, 'rb')
            ftp = ftplib.FTP(self.server)
            ftp.login(self.username, self.password)
            ftp.storbinary('STOR ' + self.filename, hiscore_file)
            hiscore_file.close()
            ftp.quit()
            return True
        except ftplib.all_errors:
            return False

    def draw(self):
        window.fill(0)
        y = 100
        for tu in self.hiscore_data_tulist:
            text = font.render(tu[0] + ' ' + str(tu[1]), True, color.text)
            self.text_rec = text.get_rect()
            self.text_rec.center = (200, y)
            window.blit(text, self.text_rec)
            y += 60
        pygame.display.update()


# hiscore = Hiscore('gbhiscore.txt')
# hiscore.save_remote_file()
# hiscore.draw()
# pygame.time.delay(5000)
# window.fill(0)

while not g.exit:
    if g.game_won:
        info.lives += 1
        if info.lives > info.max_lives:
            info.lives = info.max_lives
        g.track_index += 1
        if g.track_index >= len(target_positions.data):
            target_positions.reset()
            block_positions.reset()
            g.track_index = 0
        targets.reset()
        blocks.reset()
        defender.reset()
        ball.reset()
        frame.reset()
        shaders.reset()
        g.game_won = False

    if g.game_lost:
        info.lives -= 1
        if info.lives <= 0:
            info.reset()
            g.track_index = 0
        target_positions.reset()
        block_positions.reset()
        defender.reset()
        ball.reset()
        frame.reset()
        targets.reset()
        blocks.reset()
        shaders.reset()
        g.game_lost = False

    pygame.time.delay(12)
    g.display_counter += 1
    board.draw()
    ball.draw_shadow()
    defender.draw_shadow()
    targets.draw()
    shaders.draw()
    blocks.draw()
    ball.draw()
    defender.draw()
    info.draw()
    pygame.display.update()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            g.exit = True

    # parse keys
    keys = pygame.key.get_pressed()
    if keys[pygame.K_LEFT]:
        defender.toward = directions['left']
    elif keys[pygame.K_RIGHT]:
        defender.toward = directions['right']
    elif keys[pygame.K_UP]:
        defender.toward = directions['up']
    elif keys[pygame.K_DOWN]:
        defender.toward = directions['down']
    elif keys[pygame.K_SPACE]:
        ball.fire(defender.pos)
    elif keys[pygame.K_ESCAPE]:
        g.exit = True
    elif keys[pygame.K_w]:
        g.game_won = True
    else:
        defender.toward = directions['stopped']

    # Manage movements
    travel = (abs(ball.direction[0]) + abs(ball.direction[1]))
    if travel == 1 and g.display_counter % 3 == 0:
        ball.step()
    if travel == 2 and g.display_counter % 4 == 0:
        ball.step()
    if travel == 3 and g.display_counter % 5 == 0:
        ball.step()

    if g.display_counter % 3 == 0:
        shaders.dim()

    if g.display_counter % 2 == 0:
        defender.step()

#    if g.display_counter % 10 == 0:
#        color.block = color.dimmer(color.block, 20)
#        color.target = color.dimmer(color.target, 30)

#    if g.display_counter % 40 == 0:
#        color.ball = color.dimmer(color.ball, 20)

# We have fallen off the main loop, so this is the end
pygame.quit()
