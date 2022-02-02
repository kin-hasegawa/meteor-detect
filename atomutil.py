#!/usr/bin/env python

from pathlib import Path
import argparse
import cv2

import telnetlib

from atomcam import DetectMeteor, ATOM_CAM_IP, check_clock


def make_ftpcmd(meteor_list):
    '''
    検出されたログから画像をダウンロードするFTPコマンドを生成する。
    '''
    with open(meteor_list, "r") as f:
        for line in f.readlines():
            if line.startswith('#'):
                continue

            (date, time) = line.split()[0:2]
            hh, mm, ss = time.split(':')

            date_dir = ''.join(date.split('/'))

            print("wget -nc -r -nv -nH --cut-dirs=3 ftp://root:atomcam2@{}/media/mmc/record/{}/{}/{}.mp4".format(ATOM_CAM_IP, date_dir, hh, mm))


def detect_meteors(meteor_list):
    '''
    検出された流星リストから再検出(修正中)
    '''
    with open(meteor_list, "r") as f:
        prev_file = None
        for line in f.readlines():
            if line.startswith('#'):
                continue

            (date, time) = line.split()[0:2]
            date_dir = ''.join(date.split('/'))

            hh, mm, ss = time.split(':')

            file_path = Path(date_dir, hh, "{}.mp4".format(mm))

            if file_path != prev_file:
                print(file_path)
                detecter = DetectMeteor(str(file_path))
                detecter.meteor(2)

                prev_file = file_path


def make_movie(meteor_list, output="movie.mp4"):
    '''
    検出された流星リストから動画作成(未完成)
    '''
    data_dir = Path(meteor_list).stem

    # とりあえずATOM Camサイズ
    size = (1920, 1080)
    fourcc = cv2.VideoWriter_fourcc('m', 'p', '4', 'v')
    video = cv2.VideoWriter(output, fourcc, 0.5, size)

    with open(meteor_list, "r") as f:
        for line in f.readlines():
            if line.startswith('#'):
                continue

            (date, time) = line.split()[0:2]
            date_str = ''.join(date.split('/'))

            hh, mm, ss = time.split(':')
            filename = "{}{}{}{}.jpg".format(date_str, hh, mm, ss)
            file_path = str(Path(data_dir, filename))

            print(file_path)
            img = cv2.imread(file_path)
            video.write(img)

        video.release()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('meteors', nargs='?', help="List of detected meteors (text file)")
    parser.add_argument('-f', '--ftp', action='store_true', help='FTPコマンド作成')
    parser.add_argument('-m', '--movie', action='store_true', help='FTPコマンド作成')
    parser.add_argument('-o', '--output', default='movie.mp4', help='動画ファイル名(.mp4)')
    parser.add_argument('-c', '--clock', action='store_true', help='ATOM Camの時計のチェック')

    args = parser.parse_args()

    # print("# {}".format(args.meteors))

    if args.ftp:
        make_ftpcmd(args.meteors)
    elif args.movie:
        make_movie(args.meteors, args.output)
    elif args.clock:
        check_clock()
    else:
        detect_meteors(args.meteors)
