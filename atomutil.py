#!/usr/bin/env python

from pathlib import Path
import argparse
import cv2

from atomcam import DetectMeteor, ATOM_CAM_IP, ATOM_CAM_USER, ATOM_CAM_PASS
from atomcam import check_clock, set_clock , AtomSsh , AtomTelnet


def make_ftpcmd(meteor_list, directory):
    '''
    検出されたログから画像をダウンロードするFTPコマンドを生成する。
    '''
    wget = "wget -nc -r -nv -nH --cut-dirs=3"
    if directory:
        wget += " -P {}".format(directory)

    with open(meteor_list, "r") as f:
        for line in f.readlines():
            if line.startswith('#'):
                continue

            # 検出時刻から動画ファイル名を生成する。
            (date, time) = line.split()[0:2]
            hh, mm, ss = time.split(':')
            date_dir = ''.join(date.split('/'))
            mp4_file = "{}/{}/{}.mp4".format(date_dir, hh, mm)
            url = "ftp://{}:{}@{}/media/mmc/record/{}".format(
                ATOM_CAM_USER, ATOM_CAM_PASS, ATOM_CAM_IP, mp4_file
            )
            print("{} {}".format(wget, url))


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


def make_movie(meteor_list, output="movie.mp4", fps=1.0):
    '''
    検出された流星リストから動画作成(未完成)

    Args:
      meteor_list: 検出された流星のログファイル
      outout: 出力動画ファイル名
    '''
    data_dir = Path(meteor_list).parents[0]
    date_dir = Path(meteor_list).stem

    # とりあえずATOM Camサイズ
    size = (1920, 1080)
    fourcc = cv2.VideoWriter_fourcc('m', 'p', '4', 'v')
    print(f'FPS={fps}')
    video = cv2.VideoWriter(output, fourcc, fps, size)

    with open(meteor_list, "r") as f:
        for line in f.readlines():
            if line.startswith('#'):
                continue

            (date, time) = line.split()[0:2]
            date_str = ''.join(date.split('/'))

            hh, mm, ss = time.split(':')
            filename = "{}{}{}{}.jpg".format(date_str, hh, mm, ss)
            file_path = str(Path(data_dir, date_dir, filename))

            print(file_path)
            try:
                img = cv2.imread(file_path)
                video.write(img)
            except Exception as e:
                print(str(e))

        video.release()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('meteors', nargs='?', help="List of detected meteors (text file)")
    parser.add_argument('-f', '--ftp', action='store_true', help='FTPコマンド作成')
    parser.add_argument('-d', '--directory', default=None, help='FTPコマンド取得先ディレクトリ名')
    parser.add_argument('-m', '--movie', action='store_true', help='FTPコマンド作成')
    parser.add_argument('-o', '--output', default='movie.mp4', help='動画ファイル名(.mp4)')
    parser.add_argument('-c', '--clock', action='store_true', help='ATOM Camの時計のチェック')
    parser.add_argument('-s', '--set_clock', action='store_true', help='ATOM Camの時計をホスト側に合わせる')
    parser.add_argument('-r', '--remote', default='telnet', choices=['telnet','ssh'], help='ATOM Cam へのリモート接続で使う client')

    args = parser.parse_args()

    # print("# {}".format(args.meteors))

    shell = None
    if(args.remote == 'ssh'):
        shell = AtomSsh(ATOM_CAM_IP)
    else:
        shell = AtomTelnet(ATOM_CAM_IP)
    
    if args.ftp:
        make_ftpcmd(args.meteors, args.directory)
    elif args.movie:
        make_movie(args.meteors, args.output, args.fps)
        #make_movie(args.meteors, args.output)
    elif args.clock:
        check_clock(shell)
    elif args.set_clock:
        set_clock(shell)
    else:
        detect_meteors(args.meteors)
