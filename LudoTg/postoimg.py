from PIL import Image, ImageDraw, ImageFont
from itertools import groupby

kor = {
    1:(105,710),
    2:(227,710),
    3:(105,832),
    4:(227,832),
    5:(105,108),
    6:(227,108),
    7:(105,230),
    8:(227,230),
    9:(708,108),
    10:(830,108),
    11:(708,230),
    12:(830,230),
    13:(708,710),
    14:(830,710),
    15:(708,832),
    16:(830,832),

    17:(400,872),
    18:(400,805),
    19:(400,738),
    20:(400,671),
    21:(400,604),
    22:(333,537),
    23:(266,537),
    24:(199,537),
    25:(132,537),
    26:(65,537),
    27:(-2,537),
    28:(-2,470),
    29:(-2,403),
    30:(65,403),
    31:(132,403),
    32:(199,403),
    33:(266,403),
    34:(333,403),
    35:(400,336),
    36:(400,269),
    37:(400,202),
    38:(400,135),
    39:(400,68),
    40:(400,1),
    41:(467,1),
    42:(534,1),
    43:(534,68),
    44:(534,135),
    45:(534,202),
    46:(534,269),
    47:(534,336),
    48:(601,403),
    49:(668,403),
    50:(735,403),
    51:(802,403),
    52:(869,403),
    53:(936,403),
    54:(936,470),
    55:(936,537),
    56:(869,537),
    57:(802,537),
    58:(735,537),
    59:(668,537),
    60:(601,537),
    61:(534,604),
    62:(534,671),
    63:(534,738),
    64:(534,805),
    65:(534,872),
    66:(534,939),
    67:(467,939),
    68:(400,939),

    69:((467,872)),
    70:((467,805)),
    71:((467,738)),
    72:((467,671)),
    73:((467,604)),
    74:((467,537)),

    75:(65,470),
    76:(132,470),
    77:(199,470),
    78:(266,470),
    79:(333,470),
    80:(400,470),

    81:(467,68),
    82:(467,135),
    83:(467,202),
    84:(467,269),
    85:(467,336),
    86:(467,403),

    87:(869,470),
    88:(802,470),
    89:(735,470),
    90:(668,470),
    91:(601,470),
    92:(534,470)
}

def generate_list(n):
    if n==1:
        return [0]
    elif n==2:
        return [-10,10]
    elif n==3:
        return [-10,0,10]
    elif n==4:
        return [-9,-3,3,9]
    elif n==5:
        return [-12,-6,0,6,12]
    elif n==6:
        return [-15,-9,-3,3,9,15]
    elif n==7:
        return [-18,-12,-6,0,6,12,18]
    elif n==8:
        return [-14,-10,-6,-2,2,6,10,14]
    elif n==9:
        return [-16,-12,-8,-4,0,4,8,12,16]
    elif n==10:
        return [-18,-14,-10,-6,-2,2,6,10,14,18]
    elif n==11:
        return [-10,-8,-6,-4,-2,0,2,4,6,8,10]
    elif n==12:
        return [-11,-9,-7,-5,-3,-1,1,3,5,7,9,11]
    elif n==13:
        return [-12,-10,-8,-6,-4,-2,0,2,4,6,8,10,12]
    elif n==14:
        return [-13,-11,-9,-7,-5,-3,-1,1,3,5,7,9,11,13]
    elif n==15:
        return [-14,-12,-10,-8,-6,-4,-2,0,2,4,6,8,10,12,14]
    elif n==16:
        return [-15,-13,-11,-9,-7,-5,-3,-1,1,3,5,7,9,11,13,15]


def pos2img(poss, players):
    poss = [
        ('q1', poss[0][0]), ('q2', poss[0][1]), ('q3', poss[0][2]), ('q4', poss[0][3]),
        ('j1', poss[1][0]), ('j2', poss[1][1]), ('j3', poss[1][2]), ('j4', poss[1][3]),
        ('s1', poss[2][0]), ('s2', poss[2][1]), ('s3', poss[2][2]), ('s4', poss[2][3]),
        ('k1', poss[3][0]), ('k2', poss[3][1]), ('k3', poss[3][2]), ('k4', poss[3][3])
    ]
    with Image.open('images/board.jpg') as board:
        draw = ImageDraw.Draw(board)
        font = ImageFont.truetype(font='font.ttf', size=24)
        draw.text(xy=(200, 965), text=players[0][:25], font=font, fill='white', stroke_width=2, stroke_fill='black', anchor='mt')
        draw.text(xy=(200, 20), text=players[1][:25], font=font, fill='white', stroke_width=2, stroke_fill='black', anchor='mt')
        draw.text(xy=(800, 20), text=players[2][:25], font=font, fill='white', stroke_width=2, stroke_fill='black', anchor='mt')
        draw.text(xy=(800, 965), text=players[3][:25], font=font, fill='white', stroke_width=2, stroke_fill='black', anchor='mt')

        poss = sorted(poss, key=lambda x: x[1], reverse=True)
        poss = [list(group) for key, group in groupby(poss, key=lambda x: x[1])]
        for pos in poss:
            set_kors = generate_list(len(pos))
            #print(set_kors)
            for k, v in enumerate(pos):
                stone = Image.open('images/'+v[0]+'.png')
                board.paste(stone, (kor[v[1]][0]+set_kors[k], kor[v[1]][1]+set_kors[k]), stone)
        return board



if __name__ == '__main__':
    pos = [[1,2,3,4],[5,6,7,8],[9,10,11,12],[13,14,15,16]]
    players = [
        '🌙 Aybek',
        'Nuraliy Dalibaev',
        'Gulistan Ataniyazova',
        'Ulzada Arzimova'
    ]
    pos2img(pos, players).save('result.jpg')
    #pos2img(pos)
    #print(generate_list(4))
    '''
    with Image.open('images/board.jpg') as board:
        draw = ImageDraw.Draw(board)
        font = ImageFont.truetype(font='arial.ttf', size=30)
        for key in kor.keys():
            draw.text(xy=kor[key], text=str(key), font=font, fill='black')
        board.save('kor.jpg')
    '''