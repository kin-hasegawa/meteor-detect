#!/usr/bin/env python

from pathlib import Path
import sys
import os
from datetime import datetime, timedelta, timezone
import time
import argparse
import numpy as np
import cv2
from imutils.video import FileVideoStream
import telnetlib


# マルチスレッド関係
import threading
import queue


# 行毎に標準出力のバッファをflushする。
sys.stdout.reconfigure(line_buffering=True)

# 自分の環境のATOM CamのIPに修正してください。
ATOM_CAM_IP = os.environ.get("ATOM_CAM_IP", "192.168.2.110")
ATOM_CAM_RTSP = "rtsp://{}:8554/unicast".format(ATOM_CAM_IP)

# atomcam_toolsでのデフォルトのユーザアカウントなので、自分の環境に合わせて変更してください。
ATOM_CAM_USER = "root"
ATOM_CAM_PASS = "atomcam2"


class AtomTelnet():
    '''
    ATOM Camにtelnet接続し、コマンドを実行するクラス
    '''
    def __init__(self, ip_address=ATOM_CAM_IP):
        self.tn = telnetlib.Telnet(ip_address)
        self.tn.read_until(b"login: ")
        self.tn.write(ATOM_CAM_USER.encode('ascii') + b"\n")
        self.tn.read_until(b"Password: ")
        self.tn.write(ATOM_CAM_PASS.encode('ascii') + b"\n")

        self.tn.read_until(b"# ")

    def exec(self, command):
        self.tn.write(command.encode('utf-8') + b'\n')
        ret = self.tn.read_until(b"# ").decode('utf-8').split("\r\n")[1]
        return ret

    def exit(self):
        self.tn.write("exit".encode('utf-8') + b"\n")

    def __del__(self):
        self.exit()


def check_clock():
    """ATOM Camのクロックとホスト側のクロックの比較。
    """
    tn = AtomTelnet()
    atom_date = tn.exec('date')
    utc_now = datetime.now(timezone.utc)
    atom_now = datetime.strptime(atom_date, "%a %b %d %H:%M:%S %Z %Y")
    atom_now = atom_now.replace(tzinfo=timezone.utc)
    dt = atom_now - utc_now
    if dt.days < 0:
        delta = -(86400.0 - (dt.seconds + dt.microseconds/1e6))
    else:
        delta = dt.seconds + dt.microseconds/1e6

    print("# ATOM Cam =", atom_now)
    print("# HOST PC  =", utc_now)
    print("# ATOM Cam - Host PC = {}".format(delta))


def set_clock():
    """ATOM Camのクロックとホスト側のクロックに合わせる。
    """
    utc_now = datetime.now(timezone.utc)

    set_command = 'date -s "{}"'.format(utc_now.strftime("%Y-%m-%d %H:%M:%S"))
    print(set_command)
    tn = AtomTelnet()
    tn.exec(set_command)


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
    def __init__(self, video_url=ATOM_CAM_RTSP, output=None, end_time="0600", clock=False):
        self._running = False
        # video device url or movie file path
        self.capture = None
        self.url = video_url
        self.connect()
        self.FPS = self.capture.get(cv2.CAP_PROP_FPS)

        # 出力先ディレクトリ
        if output:
            output_dir = Path(output)
            output_dir.mkdir(exist_ok=True)
        else:
            output_dir = Path('.')
        self.output_dir = output_dir

        # MP4ファイル再生の場合を区別する。
        self.mp4 = Path(video_url).suffix == '.mp4'

        # 終了時刻を設定する。
        now = datetime.now()
        t = datetime.strptime(end_time, "%H%M")
        self.end_time = datetime(now.year, now.month, now.day, t.hour, t.minute)
        if now > self.end_time:
            self.end_time = self.end_time + timedelta(hours=24)

        print("# scheduled end_time = ", self.end_time)

        if clock:
            # 内蔵時計のチェック
            check_clock()

        # 時刻表示部分のマスクを作成
        zero = np.zeros((1080, 1920, 3), np.uint8)
        self.mask = cv2.rectangle(zero, (1390,1010),(1920,1080),(255,255,255), -1)

        self.image_queue = queue.Queue(maxsize=100)

    def __del__(self):
        now = datetime.now()
        obs_time = "{:04}/{:02}/{:02} {:02}:{:02}:{:02}".format(
            now.year, now.month, now.day, now.hour, now.minute, now.second
        )
        print("# {} stop".format(obs_time))

        self.capture.release()
        cv2.destroyAllWindows()

    def connect(self):
        if self.capture:
            self.capture.release()
        self.capture = cv2.VideoCapture(self.url)

    def stop(self):
        # thread を止める
        self._running = False

    def queue_streaming(self):
        # RTSP読み込みをthreadで行い、queueにデータを流し込む。
        print("# threading version started.")
        frame_count = int(self.capture.get(cv2.CAP_PROP_FRAME_COUNT))
        self._running = True
        while(True):
            try:
                ret, frame = self.capture.read()
                if ret:
                    # self.image_queue.put_nowait(frame)
                    self.image_queue.put(frame)
                    if self.mp4:
                        current_pos = int(self.capture.get(cv2.CAP_PROP_POS_FRAMES))
                        if current_pos >= frame_count:
                            break
                else:
                    self.connect()
                    continue

                if self._running is False:
                    break
            except Exception as e:
                print(e, file=sys.stderr)
                continue

    def dequeue_streaming(self, exposure=1, no_window=False):
        # queueからデータを読み出し流星検知、描画を行う。
        num_frames = int(self.FPS * exposure)

        while True:
            img_list = []
            for n in range(num_frames):
                frame = self.image_queue.get()

                key = chr(cv2.waitKey(1) & 0xFF)
                if key == 'q':
                    self._running = False
                    return

                if self.mp4 and self.image_queue.empty():
                    self._running = False
                    return

                img_list.append(frame)

            if len(img_list) > 2:
                self.composite_img = brightest(img_list)
                self.detect_meteor(img_list)
                if not no_window:
                    cv2.imshow('ATOM Cam2 x {} frames '.format(len(img_list)), self.composite_img)

            # ストリーミングの場合、終了時刻を過ぎたなら終了。
            now = datetime.now()
            if not self.mp4 and now > self.end_time:
                print("# end of observation at ", now)
                self._running = False
                return

    def detect_meteor(self, img_list):
        # img_listで与えられた画像のリストから流星(移動天体)を検出する。
        now = datetime.now()
        obs_time = "{:04}/{:02}/{:02} {:02}:{:02}:{:02}".format(now.year, now.month, now.day, now.hour, now.minute, now.second)

        if len(img_list) > 2:
            # 差分間で比較明合成を取るために最低3フレームが必要。
            # 画像のコンポジット(単純スタック)
            diff_img = brightest(diff(img_list, self.mask))
            try:
                if detect(diff_img) is not None:
                    print('{} A possible meteor was detected.'.format(obs_time))
                    filename = "{:04}{:02}{:02}{:02}{:02}{:02}".format(now.year, now.month, now.day, now.hour, now.minute, now.second)
                    path_name = str(Path(self.output_dir, filename + ".jpg"))
                    cv2.imwrite(path_name, self.composite_img)
            except Exception as e:
                print(e, file=sys.stderr)

    def streaming(self, exposure, no_window):
        '''
        ストリーミング再生
          exposure: 比較明合成する時間(sec)
          no_window: True .. 画面表示しない

          return 0 終了
          return 1 異常終了
        '''
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
                    # 直前のコンポジット画像があれば保存する(未実装)。
                    # print(key)
                    pass

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
                        path_name = str(Path(self.output_dir, filename + ".jpg"))
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
        self.FPS = self.capture.stream.get(cv2.CAP_PROP_FPS)
        if self.FPS < 1.0:
            # 正しく入っていない場合があるので、その場合は15固定にする(ATOM Cam限定)。
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

            # print(number, num_frames)
            if number > 2:
                try:
                    diff_img = brightest(diff(img_list, self.mask))
                    if detect(diff_img) is not None:
                        obs_time = "{}:{}".format(self.obs_time, str(count*exposure).zfill(2))
                        print('{}  A possible meteor was detected.'.format(obs_time))
                        filename = self.date_dir + self.hour + self.minute + str(count*exposure).zfill(2)
                        path_name = str(Path(output_dir, filename + ".jpg"))
                        # cv2.imwrite(filename + ".jpg", diff_img)
                        composite_img = brightest(img_list)
                        cv2.imwrite(path_name, composite_img)
                except Exception as e:
                    # print(traceback.format_exc(), file=sys.stderr)
                    print(e, file=sys.stderr)


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
        print("#", file_path)
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
    (スレッドなし版、いずれ削除する。)
    '''
    if args.url:
        atom = AtomCam(args.url, args.output, args.to)
        if not atom.capture.isOpened():
            return

    now = datetime.now()
    obs_time = "{:04}/{:02}/{:02} {:02}:{:02}:{:02}".format(
        now.year, now.month, now.day, now.hour, now.minute, now.second
    )
    print("# {} start".format(obs_time))

    while True:
        sts = atom.streaming(args.exposure, args.no_window)
        if sts == 1:
            if Path(args.url).suffix == '.mp4':
                # MP4ファイルの場合は終了する。
                return

            # 異常終了した場合に再接続する
            time.sleep(5)
            print("# re-connectiong to ATOM Cam ....")
            atom = AtomCam(args.url, args.output, args.to)
        else:
            return


def streaming_thread(args):
    '''
    RTSPストリーミング、及び動画ファイルからの流星の検出(スレッド版)
    '''
    if args.url:
        atom = AtomCam(args.url, args.output, args.to, args.clock)
        if not atom.capture.isOpened():
            return

    now = datetime.now()
    obs_time = "{:04}/{:02}/{:02} {:02}:{:02}:{:02}".format(
        now.year, now.month, now.day, now.hour, now.minute, now.second
    )
    print("# {} start".format(obs_time))

    # スレッド版の流星検出
    t_in = threading.Thread(target=atom.queue_streaming)
    t_in.start()

    try:
        atom.dequeue_streaming(args.exposure, args.no_window)
    except KeyboardInterrupt:
        atom.stop()

    t_in.join()
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

    # threadモード
    parser.add_argument('--thread', default=True, action='store_true', help='スレッドテスト版')
    parser.add_argument('-c', '--clock', action='store_true', help='カメラの時刻チェック')

    parser.add_argument('--help', action='help', help='show this help message and exit')

    args = parser.parse_args()

    if args.date:
        # 日付がある場合はファイル(ATOMCam形式のファイル)から流星検出
        detect_meteor(args)
    elif args.thread:
        # ストリーミング/動画(MP4)の再生、流星検出
        streaming_thread(args)
    else:
        # ストリーミング/動画(MP4)の再生(旧バージョン)
        streaming(args)
