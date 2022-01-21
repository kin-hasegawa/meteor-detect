# meteor-detect

ATOMCamのストリーミング及びデータからの流星を自動検出<br>
Automatic detecton of meteors in movie files and streaming devices(RTSP)

無保証、無サポートです。

## 準備

ATOM Cam 2 及び、Python 3.8以上で動作確認(macOS, Ubuntu)。

* atomcam_tools.zip
* OpenCV

### atomcam-toolsのインストール

atomcam-tools は、ATOM Cam RTSPサーバー、FTP、TELNETサーバー等の機能を追加するツールです。
SDカードにダウンロードしたファイルをコピーしてカメラの再起動を行うだけでインストールができます。

以下のサイトから atomcam_tools.zip をダウンロードしてATOM Cam2にインストールします。

- [ATOMCam2の機能拡張用ツールを公開しました](https://honeylab.hatenablog.jp/entry/2021/09/24/002107)
- [ダウンロード](https://github.com/bakueikozo/atomcam_tools/releases/download/v1.0rc/atomcam_tools.zip)

インストール直後の

### OpenCVのインストール

OpenCVはC/C++で書かれた強力な画像処理ライブラリで、Pythonから利用することができる。

#### macOS/Ubuntuの場合

```
% pip install ffmpeg
% pip install opencv-python
% pip install imutils
```

## データ

ATOM Camからのデータは、SDカードあるいは atomcam_tools によるFTPダウンロードします。

ディレクトリ構造は日付毎に以下のようになっています。

```
% tree 20220114
20220114
└── 23
    ├── 00.mp4
    ├── 01.mp4
    ├── 02.mp4
    ├── 03.mp4
    ├── 04.mp4

以下省略

```

### データのダウンロード

wgetコマンドを使うとまとめてダウンロードすることができます。

日付を指定して一括ダウンロードする例:

```
% wget -r -nv -nH --cut-dirs=3 ftp://root:atomcam2@192.168.2.111/media/mmc/record/20220104
```

日付時刻を指定して1時間分のデータをダウンロードする例:

```
% wget -r -nv -nH --cut-dirs=3 ftp://root:atomcam2@192.168.2.111/media/mmc/record/20220104/01
```

wgetコマンドのインストール方法

#### macOS

```
% brew install wget
```

#### Ubuntu

```
$ sudo apt install wget
```

#### FTPスクリプト

指定範囲のデータをまとめてダウンロードするためのスクリプト(atom_ftp.sh)を用意しました。

```
% ./atom_ftp.sh 20220104 1 2
```

とやることで、カレントディレクトリ以下に指定時刻(1〜2時)のデータをダウンロードできます。

```
20220104/01/*.mp4
20220104/02/*.mp4
```

## 流星検出方法

1. 流星が流れる時間程度(1~2秒)で比較明合成を行う。
1. 比較明合成した画像の差分を取り、移動天体を抽出する。
1. 移動天体の中から流星と思われる直線状のパターンを検出する。
1. 検出メッセージ(時刻)を出力し、その比較明合成画像を保存する。

流星と飛行機、人工衛星の区別がまだ十分にできていない。また、東京の空ではS/Nが悪いため暗い流星は検出できない。

画像からの流星の検出方法は下記のサイトで紹介されている方法を参考にした。

[D64.NL – METEOR DETECTING PROJECT](https://www.meteornews.net/2020/05/05/d64-nl-meteor-detecting-project/)

## 使い方

ソースコードの下記の行を自分のATOM CamのIPに合わせて修正してください。

```
# 自分の環境のATOM CamのIPアドレスに変更してください。
ATOM_CAM_RTSP = 'rtsp://192.168.2.111:8554/unicast'
```

以下は、コマンドオプションの一覧。

```
% ./atomcam.py --help
usage: atomcam.py [-u URL] [-n] [-d DATE] [-h HOUR] [-m MINUTE] [-i INPUT] [-e EXPOSURE] [-o OUTPUT]
                  [--help]

optional arguments:
  -u URL, --url URL     RTSPのURL、または動画(MP4)ファイル
  -n, --no_window       画面非表示
  -d DATE, --date DATE  Date in 'yyyymmdd' format (JST)
  -h HOUR, --hour HOUR  Hour in 'hh' format (JST)
  -m MINUTE, --minute MINUTE
                        minute in mm (optional)
  -i INPUT, --input INPUT
                        検出対象のTOPディレクトリ名
  -e EXPOSURE, --exposure EXPOSURE
                        露出時間(second)
  -o OUTPUT, --output OUTPUT
                        検出画像の出力先ディレクトリ名
  --help                show this help message and exit
```

### リアルタイムに流星検出を行う

`atomcam.py`コマンドがあるディレクトリ下での実行を想定しています。

デフォルト状態での実行例

```
% ./atomcam.py
```

デフォルトのRTSPサーバーからストリーミングサーバーからデータを読み込み、流星検出を試みる。ウインドウが表示され、比較明合成画像が1秒毎に更新される。流星が検出されると日時とメッセージがコンソールに出力される。

以下はコマンドの出力例。この例で見つかっているのは飛行機。

```
# 2022/01/15 00:00:00 started.
2022/01/15 00:19:31 A possible meteor was detected.
2022/01/15 00:19:34 A possible meteor was detected.
2022/01/15 00:19:37 A possible meteor was detected.
2022/01/15 00:19:39 A possible meteor was detected.
2022/01/15 00:19:42 A possible meteor was detected.
...
```

teeコマンドを合わせて使うと、画面にログを表示すると共に、ファイルに書き出すことができる。

```
% ./atomcam.py | tee -a 20220104.log
```

teeコマンドの`-a`オプションは追記で、オプションなしの場合は上書きされる。

### 動画ファイル(ATOM Cam形式のディレクトリ4)から流星検出を行う

date=20220109 の日付の 01時台の1時間分のデータから流星検出を行う。

```
% ./atomcam.py -d 20220109 -h 01
```

### 動画ファイル(MP4)から流星検出を行う

```
% ./atomcam.py -u 20220109/01/05.mp4
```

