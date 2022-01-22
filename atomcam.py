#!/usr/bin/env python

from pathlib import Path
import sys
import os
from datetime import datetime, timedelta
import time
import argparse
import numpy as np
import cv2
from imutils.video import FileVideoStream

# 行毎に標準出力のバッファをflushする。
sys.stdout.reconfigure(line_buffering=True)

# 自分の環境のATOM CamのIPに修正してください。
ATOM_CAM_IP = os.environ.get("ATOM_CAM_IP", "192.168.2.110")
ATOM_CAM_RTSP = "rtsp://{}:8554/unicast".format(ATOM_CAM_IP)


def composite(list_images):
    # 画像リストの合成
    equal_fraction = 1.0 / (len(list_images))

    output = np.zeros_like(list_images[0])

    for img in list_images:
        output = output + img * equal_fraction

    output = output.astype(np.uint8)

    return output


def brightest(img_list):
    # 比較明合成処理
    output = img_list[0]

    for img in img_list[1:]:
        output = np.where(output > img, output, img)

    return output


def diff(img_list, mask):
    # 画像リストから差分画像のリストを作成する。
    diff_list = []
    for img1, img2 in zip(img_list[:-2], img_list[1:]):
        img1 = cv2.bitwise_or(img1, mask)
        img2 = cv2.bitwise_or(img2, mask)
        diff_list.append(cv2.subtract(img1, img2))

    return diff_list


def detect(img):
    # 画像上の線状のパターンを流星として検出する。
    blur_size = (5, 5)
    blur = cv2.GaussianBlur(img, blur_size, 0)
    canny = cv2.Canny(blur, 100, 200, 3)

    # The Hough-transform algo:
    return cv2.HoughLinesP(canny, 1, np.pi/180, 25, minLineLength=30, maxLineGap=5)


class AtomCam:
    def __init__(self, video_url=ATOM_CAM_RTSP, end_time="0600"):
        print("# AtomCam")
        # video device url or movie file path
        self.capture = cv2.VideoCapture(video_url)
        self.FPS = self.capture.get(cv2.CAP_PROP_FPS)

        # MP4ファイル再生の場合を区別する。
        self.mp4 = Path(video_url).suffix == '.mp4'

        # 終了時刻を設定する。
        now = datetime.now()
        t = datetime.strptime(end_time, "%H%M")
        self.end_time = datetime(now.year, now.month, now.day, t.hour, t.minute)
        if t.hour < 12:
            self.end_time = self.end_time + timedelta(hours=24)

        print("# end_time = ", self.end_time)

        # 時刻表示部分のマスクを作成
        zero = np.zeros((1080, 1920, 3), np.uint8)
        self.mask = cv2.rectangle(zero, (1390,1010),(1920,1080),(255,255,255), -1)

    def __del__(self):
        self.capture.release()
        cv2.destroyAllWindows()

    def streaming(self, exposure, no_window, output):
        '''
        ストリーミング再生
          exposure: 比較明合成する時間(sec)
          no_window: True .. 画面表示しない
          output: 出力先ディレクトリ

          return 0 終了
          return 1 異常終了
        '''
        if output:
            output_dir = Path(output)
            output_dir.mkdir(exist_ok=True)
        else:
            output_dir = Path('.')

        num_frames = int(self.FPS * exposure)
        composite_img = None

        while(True):
            # 現在時刻を取得
            now = datetime.now()
            obs_time = "{:04}/{:02}/{:02} {:02}:{:02}:{:02}".format(now.year, now.month, now.day, now.hour, now.minute, now.second)

            key = None
            img_list = []
            for n in range(num_frames):
                try:
                    ret, frame = self.capture.read()
                except Exception as e:
                    print(e, file=sys.stderr)
                    continue

                key = chr(cv2.waitKey(1) & 0xFF)
                if key == 'q':
                    return 0

                if not ret:
                    break

                if key == 's' and composite_img:
                    # 直前のコンポジット画像があれば保存する。
                    print(key)

                img_list.append(frame)

            number = len(img_list)

            if number > 2:
                # 差分間で比較明合成を取るために最低3フレームが必要。
                # 画像のコンポジット(単純スタック)
                #composite_img = self.composite(img_list)
                # 画像のコンポジット(比較明合成)
                composite_img = brightest(img_list)
                diff_img = brightest(diff(img_list, self.mask))
                try:
                    if not no_window:
                        blur_img = cv2.medianBlur(composite_img, 3)
                        cv2.imshow('ATOM Cam2 x {} frames '.format(number), blur_img)
                        # cv2.imshow('ATOM Cam2 x {} frames '.format(number), composite_img)
                    if detect(diff_img) is not None:
                        print('{} A possible meteor was detected.'.format(obs_time))
                        filename = "{:04}{:02}{:02}{:02}{:02}{:02}".format(now.year, now.month, now.day, now.hour, now.minute, now.second)
                        path_name = str(Path(output_dir, filename + ".jpg"))
                        cv2.imwrite(path_name, composite_img)
                except Exception as e:
                    print(e, file=sys.stderr)
            else:
                print('No data: communcation lost? or end of data', file=sys.stderr)
                return 1

            # 終了時刻を過ぎたなら終了。
            now = datetime.now()
            if now > self.end_time:
                print("# end of observation at ", now)
                return 0


class DetectMeteor():
    '''
    動画ファイル(MP4)からの流星の検出
    '''
    def __init__(self, file_path):
        # video device url or movie file path
        self.capture = FileVideoStream(file_path).start()
        self.FPS = 15

        # file_pathから日付、時刻を取得する。
        date_element = file_path.split('/')
        self.date_dir = date_element[-3]
        self.date = datetime.strptime(self.date_dir, "%Y%m%d")

        self.hour = date_element[-2]
        self.minute = date_element[-1].split('.')[0]
        self.obs_time = "{}/{:02}/{:02} {}:{}".format(self.date.year, self.date.month, self.date.day, self.hour, self.minute)

        # 時刻表示部分のマスクを作成
        zero = np.zeros((1080, 1920, 3), np.uint8)
        self.mask = cv2.rectangle(zero, (1390,1010),(1920,1080),(255,255,255), -1)

    def meteor(self, exposure=1, output=None):
        '''
        流星の検出
        '''
        if output:
            output_dir = Path(output)
            output_dir.mkdir(exist_ok=True)
        else:
            output_dir = Path('.')

        print(output_dir)

        num_frames = int(self.FPS * exposure)
        composite_img = None

        count = 0
        while self.capture.more():
            img_list = []
            for n in range(num_frames):
                try:
                    if self.capture.more():
                        frame = self.capture.read()
                    else:
                        continue
                except Exception as e:
                    print(e, file=sys.stderr)
                    continue

                img_list.append(frame)

            # 画像のコンポジット
            number = len(img_list)
            count += 1

            if number > 2:
                try:
                    diff_img = brightest(diff(img_list, self.mask))
                    composite_img = brightest(img_list)
                    if detect(diff_img) is not None:
                        obs_time = "{}:{}".format(self.obs_time, str(count*exposure).zfill(2))
                        print('{}  A possible meteor was detected.'.format(obs_time))
                        filename = self.date_dir + self.hour + self.minute + str(count*exposure).zfill(2)
                        path_name = str(Path(output_dir, filename + ".jpg"))
                        # cv2.imwrite(filename + ".jpg", diff_img)
                        cv2.imwrite(path_name, composite_img)
                except Exception as e:
                    # print(traceback.format_exc(), file=sys.stderr)
                    print(e, file=sys.stderr)

            else:
                return 1


def detect_meteor(args):
    '''
    ATOM Cam形式の動画ファイルからの流星の検出
    '''
    if args.input:
        # 入力ファイルのディレクトリの指定がある場合
        input_dir = Path(args.input)
    else:
        input_dir = Path('.')

    data_dir = Path(input_dir, args.date)
    if args.hour:
        # 時刻(hour)の指定がある場合
        data_dir = Path(data_dir, args.hour)
        if args.minute:
            # 1分間のファイル単体の処理
            file_path = Path(data_dir, "{}.mp4".format(args.minute))

    # print(data_dir)

    if args.minute:
        # 1分間の単体のmp4ファイルの処理
        print(file_path)
        detecter = DetectMeteor(str(file_path))
        detecter.meteor(args.exposure, args.output)
    else:
        # 1時間内の一括処理
        for file_path in sorted(Path(data_dir).glob("*.mp4")):
            print('#', Path(file_path))
            detecter = DetectMeteor(str(file_path))
            detecter.meteor(args.exposure, args.output)


def streaming(args):
    '''
    RTSPストリーミング、及び動画ファイルからの流星の検出
    '''
    if args.url:
        atom = AtomCam(args.url, args.to)
        if not atom.capture.isOpened():
            return

    now = datetime.now()
    obs_time = "{:04}/{:02}/{:02} {:02}:{:02}:{:02}".format(
        now.year, now.month, now.day, now.hour, now.minute, now.second
    )
    print("# {} start".format(obs_time))

    while True:
        sts = atom.streaming(args.exposure, args.no_window, args.output)
        if sts == 1:
            if Path(args.url).suffix == '.mp4':
                # MP4ファイルの場合は終了する。
                return

            # 異常終了した場合に再接続する
            time.sleep(5)
            atom = AtomCam(args.url, args.to)
        else:
            return


if __name__ == '__main__':
    parser = argparse.ArgumentParser(add_help=False)

    # ストリーミングモードのオプション
    parser.add_argument('-u', '--url', default=ATOM_CAM_RTSP, help='RTSPのURL、または動画(MP4)ファイル')
    parser.add_argument('-n', '--no_window', action='store_true', help='画面非表示')

    # 以下はATOM Cam形式のディレクトリからデータを読む場合のオプション
    parser.add_argument('-d', '--date', default=None, help="Date in 'yyyymmdd' format (JST)")
    parser.add_argument('-h', '--hour', default=None, help="Hour in 'hh' format (JST)")
    parser.add_argument('-m', '--minute', default=None, help="minute in mm (optional)")
    parser.add_argument('-i', '--input', default=None, help='検出対象のTOPディレクトリ名')

    # 共通オプション
    parser.add_argument('-e', '--exposure', type=int, default=1, help='露出時間(second)')
    parser.add_argument('-o', '--output', default=None, help='検出画像の出力先ディレクトリ名')
    parser.add_argument('-t', '--to', default="0600", help='終了時刻(JST) "hhmm" 形式(ex. 0600)')

    parser.add_argument('--help', action='help', help='show this help message and exit')

    args = parser.parse_args()

    if args.date:
        # 日付がある場合はファイル(ATOMCam形式のファイル)から流星検出
        # detect_meteor(args.date, args.hour, args.minute, args.exposure)
        detect_meteor(args)
    else:
        # ストリーミング/動画(MP4)の再生
        streaming(args)
