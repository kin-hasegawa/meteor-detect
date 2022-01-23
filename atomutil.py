#!/usr/bin/env python

from pathlib import Path
import argparse

from atomcam import DetectMeteor, ATOM_CAM_IP


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

            print("wget -r -nv -nH --cut-dirs=3 ftp://root:atomcam2@{}/media/mmc/record/{}/{}/{}.mp4".format(ATOM_CAM_IP, date_dir,hh, mm))


def make_movie(meteor_list):
    '''
    検出された動画から再検出(修正中)
    '''
    with open(meteor_list, "r") as f:
        prev_file = None
        for line in f.readlines():

            (date, time) = line.split()[0:2]
            hh, mm, ss = time.split(':')
            file_path = Path(date, hh, "{}.mp4".format(mm))

            if file_path != prev_file:
                print(file_path)
                detecter = DetectMeteor(str(file_path))
                detecter.meteor(2)

                prev_file = file_path


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('meteors', help="List of detected meteors (text file)")
    parser.add_argument('-f', '--ftp', action='store_true', help='FTPコマンド作成')

    args = parser.parse_args()

    print("# {}".format(args.meteors))

    if args.ftp:
        make_ftpcmd(args.meteors)
    else:
        make_movie(args.meteors)
